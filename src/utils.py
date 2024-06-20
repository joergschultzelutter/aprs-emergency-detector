#
# APRS Emergency Detector
# Module: various utility functions used by the program
# Author: Joerg Schultze-Lutter, 2024
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

import configparser
from unidecode import unidecode
import re
import logging
import sys
import argparse
import string
import os.path
from aed_definitions import (
    AED_MICE_COMMITTED,
    AED_MICE_EMERGENCY,
    AED_MICE_PRIORITY,
    AED_MICE_RETURNING,
    AED_MICE_SPECIAL,
    AED_MICE_EN_ROUTE,
    AED_MICE_IN_SERVICE,
    AED_MICE_OFF_DUTY,
)
from expiringdict import ExpiringDict


# Set up the global logger variable
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)


def get_program_config_from_file(config_filename: str = "aed.cfg"):
    """
    Get the program configuration from its config file

    Parameters
    ==========
    config_filename: 'str'
                    Config file name

    Returns
    =======
    success: 'bool'
        True if successful
    aed_active_categories: 'list'
        List item, containing the Mic-E categories that we want to examine
    aed_lat: 'float'
        Latitude of the user's position
    aed_lon: 'float'
        Longitude
    aed_range_limit: 'int'
        range detection limit in km, relative to our position
        see https://www.aprs-is.net/javAPRSFilter.aspx (Range filter) for details
        'None' if no value has been specified
    """
    config = configparser.ConfigParser()

    try:
        config.read(config_filename)

        # get lat/lon and examine the data
        aed_watch_areas_string = config.get("aed_config", "aed_my_position")
        if "," not in aed_watch_areas_string:
            logger.info(msg="Config file error; invalid lat/lon position")
            raise ValueError("Error in config file")
        latlon = aed_watch_areas_string.split(",", 1)
        if len(latlon) < 2:
            logger.info(msg="Config file error; invalid lat/lon position")
            raise ValueError("Error in config file")
        lat_str = latlon[0]
        lon_str = latlon[1]

        try:
            aed_lat = float(lat_str)
            aed_lon = float(lon_str)
        except (ValueError, OverflowError):
            logger.info(msg="Config file error; invalid lat/lon position")
            raise ValueError("Error in config file")

        if abs(aed_lat) > 90.0 or abs(aed_lon) > 180.0:
            logger.info(msg="Config file error; invalid lat/lon position")
            raise ValueError("Error in config file")

        # get the list of Mic-E categories that we are to examine
        aed_acs = config.get("aed_config", "aed_active_categories")
        aed_active_categories_raw = [
            s.strip().upper() for s in aed_acs.split(",") if aed_acs != ""
        ]
        # remove any potential dupes
        aed_active_categories = list(set(aed_active_categories_raw))
        if len(aed_active_categories) == 0:
            logger.info(
                msg="Config file error; at least one APRS Mic-E category needs to be specified"
            )
            raise ValueError("Error in config file")

        for ac in aed_active_categories:
            if ac not in [
                AED_MICE_OFF_DUTY,
                AED_MICE_EN_ROUTE,
                AED_MICE_IN_SERVICE,
                AED_MICE_RETURNING,
                AED_MICE_COMMITTED,
                AED_MICE_SPECIAL,
                AED_MICE_PRIORITY,
                AED_MICE_EMERGENCY,
            ]:
                logger.info(msg=f"Config file error; received category '{ac}'")
                raise ValueError("Error in config file")

        # Get the range limit
        aed_range_limit_string = config.get("aed_config", "aed_range_limit")

        aed_range_limit = None
        if aed_range_limit_string != "NONE":
            try:
                aed_range_limit = int(aed_range_limit_string)
            except ValueError:
                aed_range_limit = None

        success = True
    except Exception as ex:
        logger.info(
            msg="Error in configuration file; Check if your config format is correct."
        )
        aed_lat = aed_lon = aed_range_limit = None
        aed_active_categories = None
        success = False

    return (
        success,
        aed_active_categories,
        aed_lat,
        aed_lon,
        aed_range_limit,
    )


def signal_term_handler(signal_number, frame):
    """
    Signal handler for SIGTERM signals. Ensures that the program
    gets terminated in a safe way, thus allowing all databases etc
    to be written to disc.

    Parameters
    ==========
    signal_number:
                    The signal number
    frame:
                    Signal frame

    Returns
    =======
    """

    logger.info(msg="Received SIGTERM; forcing clean program exit")
    sys.exit(0)


def does_file_exist(file_name: str):
    """
    Checks if the given file exists. Returns True/False.

    Parameters
    ==========
    file_name: str
                    our file name
    Returns
    =======
    status: bool
        True /False
    """
    return os.path.isfile(file_name)


def convert_text_to_plain_ascii(message_string: str):
    """
    Converts a string to plain ASCII

    Parameters
    ==========
    message_string: 'str'
                    Text that needs to be converted

    Returns
    =======
    hex-converted text to the user
    """
    message_string = (
        message_string.replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    message_string = unidecode(message_string)

    # replace non-permitted APRS characters from the
    # message text
    # see APRS specification pg. 71
    message_string = re.sub("[{}|~]+", "", message_string)

    return message_string


def time_to_live_check(interval_value):
    """
    Helper method for 'get_command_line_params'

    Parameters
    ==========
    interval_value: 'int'
                    Value that we need to check

    Returns
    =======
    interval_value: 'int'
        our checked value
    """
    interval_value = int(interval_value)
    if interval_value < 15:
        raise argparse.ArgumentTypeError("Minimum TTL is 15 (minutes)")
    return int(interval_value)


def get_command_line_params():
    """
    Gets the program command lines and runs a few pre-checks
    (e.g. if the config file exists etc)

    Parameters
    ==========

    Returns
    =======
    aed_configfile: 'str'
        program config file. MUST be present
    aed_messenger_configfile: 'str'
        Apprise YAML config file for 'full' messages
    aed_sms_messenger_configfile: 'str'
        Apprise YAML config file for 'abbreviated' messages
    generate-test-message: 'bool'
        True in case a test message is to be generated
    aed_time_to_live: 'int'
        Time-to-live in minutes for the expiring dictionary
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--configfile",
        default="aed.cfg",
        type=argparse.FileType("r"),
        help="Program config file name",
    )

    parser.add_argument(
        "--messenger-config-file",
        default=None,
        type=str,
        help="Config file name for regular messenger full-content messages",
    )

    parser.add_argument(
        "--sms-messenger-config-file",
        default=None,
        type=str,
        help="Config file name for sms-like messengers",
    )

    parser.add_argument(
        "--generate-test-message",
        dest="generate_test_message",
        action="store_true",
        help="Generates a generic test message (whereas this config is enabled) and exits the program",
    )

    parser.add_argument(
        "--ttl",
        dest="time_to_live",
        default=4 * 60,
        type=time_to_live_check,
        help="Message 'time to live' setting in minutes. Default value is 240m mins = 4h",
    )

    parser.set_defaults(generate_test_message=False)

    args = parser.parse_args()

    aed_configfile = args.configfile.name
    aed_messenger_configfile = args.messenger_config_file
    aed_sms_messenger_configfile = args.sms_messenger_config_file
    aed_generate_test_message = args.generate_test_message
    aed_time_to_live = args.time_to_live

    # Did the user specify an optional generic full message file?
    # if yes, check if that file exists
    if aed_messenger_configfile:
        if not does_file_exist(aed_messenger_configfile):
            logger.error(
                msg=f"Provided messenger config file '{aed_messenger_configfile}' does not exist"
            )
            raise ValueError("Configuration file error")

    # Did the user specify an optional generic message file for SMS messengers?
    # if yes, check if that file exists
    if aed_sms_messenger_configfile:
        if not does_file_exist(aed_sms_messenger_configfile):
            logger.error(
                msg=f"Provided short message config file '{aed_sms_messenger_configfile}' does not exist"
            )
            raise ValueError("Configuration file error")

    if not aed_messenger_configfile and not aed_sms_messenger_configfile:
        logger.error(
            msg="At least one Apprise messenger config file needs to be specified; check the program documentation"
        )
        raise ValueError("Configuration file error")

    return (
        aed_configfile,
        aed_messenger_configfile,
        aed_sms_messenger_configfile,
        aed_time_to_live,
        aed_generate_test_message,
    )


def set_message_cache_entry(
    message_cache: ExpiringDict,
    callsign: str,
    latitude: float,
    longitude: float,
    speed: float,
    course: int,
    category: str,
):
    """
    Adds our updates the decaying cache

    Parameters
    ==========
    callsign: 'str'
        User's callsign
    latitude: 'float'
        message latitude
    longitude: 'float'
        message longitude
    speed: 'float'
        message course
    course: 'int'
        message course
    category: 'str'
        Mic-E message category

    Returns
    =======
    success: 'bool'
        True if we added OR updated an entry and
             need to send messages to the user
        False if we still have the same message in
              our cache and are not required to send
              a message
    """

    # generate the potential payload
    # values have already been rounded in the main function
    # Therefore, we can process them as is
    payload = {
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "course": course,
        "category": category,
    }

    if callsign == "IU2PLZ-7":
        pass
        pass
        pass

    # New entry?
    if callsign not in message_cache:
        message_cache[callsign] = payload
        # indicate that we did something
        return True

    # We have an existing payload; let's retrieve it
    existing_payload = message_cache[callsign]

    # now compare the current payload with the existing one
    if (
        existing_payload["latitude"] == payload["latitude"]
        and existing_payload["longitude"] == payload["longitude"]
        and existing_payload["speed"] == payload["speed"]
        and existing_payload["course"] == payload["course"]
        and existing_payload["category"] == payload["category"]
    ):
        # nothing to do; we will not send that message to the user
        # as it is still in our decaying cache
        logger.info(f"DUPE: {callsign}")
        return False

    # we have at least one value that has changed. Update the existing
    # entry with the new payload and tell the main function that
    # we have to send a message to the user
    message_cache[callsign] = payload

    return True


if __name__ == "__main__":
    pass
