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
from apprise.attachment.memory import AttachMemory
import sys
import staticmaps
import io

# Set up the global logger variable
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)


def generate_apprise_message(
    apprise_config_file: str,
    callsign: str,
    latitude: float,
    longitude: float,
    course: int,
    speed: float,
    abbreviated_message_format: bool = False,
):
    """
    Generates Apprise messages and triggers transmission to the user

    Parameters
    ==========
    apprise_config_file: 'str'
        Apprise Yaml configuration file
    abbreviated_message_format: 'bool'
        False: Generate a full-text message
        True: generate 1..n SMS-like messages without image, title et al
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

    # Initialize
    attach = AttachMemory(content="attachment-content-here")

    if abbreviated_message_format:
        apprise_body = (
            f"!Emergency Beacon! CS {callsign} Pos:xxxx Spd:{speed:.1f} Dir:{course}"
        )
    else:
        apprise_body = "blah blah"

    # We are done with preparing the message body
    # Create the message header
    apprise_header = f"<u><i>APRS Emergency Detector</i></u>\n\n"

    # Set Apprise's notify icon
    notify_type = apprise.NotifyType.FAILURE

    # Send the notification
    if abbreviated_message_format:
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
            #        attach=html_image,
            notify_type=notify_type,
        )

    success = True

    logger.debug(msg="Finished Apprise message processing")
    return success


def render_png_map(
    aprs_latitude: float = None,
    aprs_longitude: float = None,
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

    Returns
    =======
    iobuffer : 'bytes'
            'None' if not successful, otherwise binary representation
            of the image
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

    return view


if __name__ == "__main__":
    pass
