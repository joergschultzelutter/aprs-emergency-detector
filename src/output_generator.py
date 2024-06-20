#
# APRS Emergency Detector
# Module: Output generator
# Author: Joerg Schultze-Lutter, 2024
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
import logging
import apprise
import os
import tempfile

apprise_memory_attachment_present = False
try:
    from apprise.attachment.memory import AttachMemory

    apprise_memory_attachment_present = True
except ModuleNotFoundError:
    pass
import sys
import staticmaps
import io
from geo_conversion_modules import (
    convert_latlon_to_mgrs,
    convert_latlon_to_dms,
    convert_latlon_to_utm,
    convert_latlon_to_maidenhead,
    haversine,
)
from utils import does_file_exist

# Set up the global logger variable
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)


def generate_apprise_message(
    apprise_config_file: str,
    callsign: str,
    latitude_aprs: float,
    longitude_aprs: float,
    latitude_aed: float,
    longitude_aed: float,
    course: int,
    speed: float,
    category: str,
    abbreviated_message_format: bool = False,
):
    """
    Generates Apprise messages and triggers transmission to the user

    Parameters
    ==========
    apprise_config_file: 'str'
        Apprise Yaml configuration file
    callsign: 'str'
        User who sent the message
    latitude_aprs: 'float'
        APRS User's latitude
    longitude_aprs: 'float"
        APRS User's longitude
    latitude_aed: 'float'
        AED User's latitude
    longitude_aed: 'float"
        AED User's longitude
    course: 'int'
        User's course
    speed: 'float'
        user's speed
    category: 'str'
        Human-readable Mic-E category, e.g. EN_ROUTE
    abbreviated_message_format: 'bool'
        False: Generate a full-text message
        True: generate SMS-like message without image, title et al
    Returns
    =======
    success: 'bool'
        True if successful
    """

    # predefine the output value
    success = False

    logger.debug(msg="Starting Apprise message processing")

    if not os.path.isfile(apprise_config_file):
        logger.error(
            msg=f"Apprise config file {apprise_config_file} does not exist; aborting"
        )
        return False

    # We want multi-line HTML messages. <br> does not work in e.g. Telegram
    newline = "\n"

    # Create the Apprise instance
    apobj = apprise.Apprise()

    # Create an Config instance
    config = apprise.AppriseConfig()

    # Add a configuration source:
    config.add(apprise_config_file)

    # Make sure to add our config into our apprise object
    apobj.add(config)

    # Create the body data
    #
    # Get the image and attach, if successful
    image_attachment = None
    apprise_attachment = None
    if not abbreviated_message_format:
        image_attachment = render_png_map(
            aprs_latitude=latitude_aprs,
            aprs_longitude=longitude_aprs,
            memory_object=apprise_memory_attachment_present,
        )

        # the image_attachment can either be an IO buffer _or_
        # a temporary file name, dependent on whether the latest
        # Apprise version is installed
        #
        # If we received a file name, we just pass it as is
        apprise_attachment = None
        if image_attachment:
            # memory obbject?
            if apprise_memory_attachment_present:
                # Initialize Apprise in-memory object
                apprise_attachment = AttachMemory(content=image_attachment)
            else:
                # String? Then simply assume that we received a file name
                # and use this one for the attachment
                if isinstance(image_attachment, str):
                    if does_file_exist(image_attachment):
                        apprise_attachment = image_attachment

    # convert lat/lon to geodata formats
    zone_number, zone_letter, easting, northing = convert_latlon_to_utm(
        latitude=latitude_aprs, longitude=longitude_aprs
    )
    geo_utm = f"{zone_number} {zone_letter} {easting} {northing}"
    geo_maidenhead = convert_latlon_to_maidenhead(
        latitude=latitude_aprs, longitude=longitude_aprs
    )
    geo_mgrs = convert_latlon_to_mgrs(latitude=latitude_aprs, longitude=longitude_aprs)

    # get the distance to the APRS coordinates
    distance, bearing, heading = haversine(
        latitude1=latitude_aed,
        longitude1=longitude_aed,
        latitude2=latitude_aprs,
        longitude2=longitude_aprs,
    )

    # Generate the body data, dependent on whether we need to send an abbreviated
    # message or not
    if abbreviated_message_format:
        apprise_body = f"!{category}! CS:{callsign} Pos:{geo_maidenhead} Spd:{speed:.1f} Dir:{course} Dst:{round(distance)}km"
    else:
        apprise_body = f"<b>Beacon '{category}' detected!</b>{newline}{newline}"
        apprise_body += f"<b>Callsign:</b> {callsign}{newline}"
        apprise_body += f"<b>Speed</b>: {speed}{newline}"
        apprise_body += f"<b>Direction</b>: {course}{newline}{newline}"
        apprise_body += (
            f"<b>Lat:</b> {latitude_aprs} / <b>Lon:</b> {longitude_aprs}{newline}"
        )
        apprise_body += f"<b>UTM:</b> {geo_utm}{newline}"
        apprise_body += f"<b>MGRS:</b> {geo_mgrs}{newline}"
        apprise_body += f"<b>Maidenhead:</b> {geo_maidenhead}{newline}{newline}"
        apprise_body += f"Distance from my location: {round(distance)} km / {round(distance*0.621371)} mi, bearing {round(bearing)} heading {heading}"

    # We are done with preparing the message body
    # Create the message header
    apprise_header = f"<u><i>APRS Emergency Beacon Detector</i></u>"

    # Set Apprise's notify icon. We want the user's attention
    # so let's go for a FAILURE icon
    notify_type = apprise.NotifyType.FAILURE

    # Send the notification, dependent on the selected mode
    if abbreviated_message_format or not apprise_attachment:
        apobj.notify(
            body=apprise_body,
            title=apprise_header,
            tag="all",
            notify_type=notify_type,
        )
    else:
        apobj.notify(
            body=apprise_body,
            title=apprise_header,
            tag="all",
            attach=apprise_attachment,
            notify_type=notify_type,
        )

    # let's get rid of the temp file, if necessary
    if not apprise_memory_attachment_present:
        # check if we deal with a temp file name
        if isinstance(apprise_attachment, str):
            # yes, we checked that one before
            # but better safe than sorry
            if does_file_exist(apprise_attachment):
                os.remove(apprise_attachment)

    success = True

    logger.debug(msg="Finished Apprise message processing")
    return success


def render_png_map(
    aprs_latitude: float = None,
    aprs_longitude: float = None,
    memory_object: bool = False,
):
    """
    Render a static PNG image of the user's destination
    and add markers based on user's lat/lon data.
    Return the binary image object back to the user
    Parameters
    ==========
    aprs_latitude : 'float'
        APRS dynamic latitude (if applicable)
    aprs_longitude : 'float'
        APRS dynamic longitude (if applicable)
    memory_object: 'bool'
        False:  write a temp file to disk (which later on
                needs to get deleted)
        True:   write to memory and do not create a temp file

    Returns
    =======
    iobuffer : 'bytes'
            'None' if not successful,
            binary representation of the image if memory_object == True
            temporary file name reference to image if memory_object == False
    """

    assert aprs_latitude, aprs_longitude

    # Create the object
    context = staticmaps.Context()
    context.set_tile_provider(staticmaps.tile_provider_OSM)

    # Add a green marker for the user's position
    marker_color = staticmaps.RED
    context.add_object(
        staticmaps.Marker(
            staticmaps.create_latlng(aprs_latitude, aprs_longitude),
            color=marker_color,
            size=12,
        )
    )

    view = None
    if memory_object:
        # create a buffer as we need to write to write to memory
        iobuffer = io.BytesIO()

        try:
            # Try to render via pycairo - looks nicer
            if staticmaps.cairo_is_supported():
                image = context.render_cairo(800, 500)
                image.write_to_png(iobuffer)
            else:
                # if pycairo is not present, render via pillow
                image = context.render_pillow(800, 500)
                image.save(iobuffer, format="png")

            # reset the buffer position
            iobuffer.seek(0)

            # get the buffer value and return it
            view = iobuffer.getvalue()
        except Exception as ex:
            view = None
    else:
        # no memory object; write to temp file instead
        # Create a temporary file name. Attach the file type as
        # extension; otherwise, Apprise will not render the image
        file_name = tempfile.NamedTemporaryFile().name + ".png"

        try:
            # assign the file name to the return value
            view = file_name
            # Try to render via pycairo - looks nicer
            if staticmaps.cairo_is_supported():
                image = context.render_cairo(800, 500)
                image.write_to_png(file_name)
            else:
                # if pycairo is not present, render via pillow
                image = context.render_pillow(800, 500)
                image.save(file_name, format="png")
        except Exception as ex:
            view = None

    return view


if __name__ == "__main__":
    pass
