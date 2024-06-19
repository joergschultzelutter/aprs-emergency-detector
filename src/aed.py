#!/usr/bin/env python3
#
# APRS Emergency Detector
# Author: Joerg Schultze-Lutter, 2024
#
# Purpose: retrieve APRS emergency messages from APRS-IS and
# send Apprise notification(s) to the user
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
import logging
import time

import aprslib
import sys
import signal
from expiringdict import ExpiringDict
from output_generator import generate_apprise_message
from utils import (
    signal_term_handler,
    get_program_config_from_file,
    get_command_line_params,
)

# APRS-IS communication parameters
# This program is only going to receive
# data; therefore, we do not need a passcode
aprsis_callsign = "N0CALL"
aprsis_passcode = "-1"
aprsis_filter = "t/p"
aprsis_server_name = "euro.aprs2.net"
aprsis_server_port = 14580
AIS = None

# These are the _possible_ Mic-E message types
APRS_MICE_OFF_DUTY = "M0: Off Duty"
APRS_MICE_EN_ROUTE = "M1: En Route"
APRS_MICE_IN_SERVICE = "M2: In Service"
APRS_MICE_RETURNING = "M3: Returning"
APRS_MICE_COMMITTED = "M4: Committed"
APRS_MICE_SPECIAL = "M5: Special"
APRS_MICE_PRIORITY = "M6: Priority"
APRS_MICE_EMERGENCY = "Emergency"

# these are the possible Mic-E message types that we might receive
# from the command line parser
AED_MICE_OFF_DUTY = "OFF_DUTY"
AED_MICE_EN_ROUTE = "EN_ROUTE"
AED_MICE_IN_SERVICE = "IN_SERVICE"
AED_MICE_RETURNING = "RETURNING"
AED_MICE_COMMITTED = "COMMITTED"
AED_MICE_SPECIAL = "SPECIAL"
AED_MICE_PRIORITY = "PRIORITY"
AED_MICE_EMERGENCY = "EMERGENCY"

# this is the command line parser vs. message_type_mapping
AED_APRS_MAPPING = {
    AED_MICE_OFF_DUTY: APRS_MICE_OFF_DUTY,
    AED_MICE_EN_ROUTE: APRS_MICE_EN_ROUTE,
    AED_MICE_IN_SERVICE: APRS_MICE_IN_SERVICE,
    AED_MICE_RETURNING: APRS_MICE_RETURNING,
    AED_MICE_COMMITTED: APRS_MICE_COMMITTED,
    AED_MICE_SPECIAL: APRS_MICE_SPECIAL,
    AED_MICE_PRIORITY: APRS_MICE_PRIORITY,
    AED_MICE_EMERGENCY: APRS_MICE_EMERGENCY,
}

# Max number of APRS TTL entries
APRS_TTL_MAX_MESSAGES = 1000

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)


def mycallback(raw_aprs_packet):
    # Unfortunately, APRS-IS does not offer a filter
    # for Mic-E messages. Therefore, we have to filter
    # these messages ourselves
    if "format" in raw_aprs_packet:
        fmt = raw_aprs_packet["format"]
        if fmt == "mic-e":
            if "mtype" in raw_aprs_packet:
                # check if the mtype is part of the list of
                # categories that we are to monitor
                mtype = raw_aprs_packet["mtype"]
                if mtype in aed_categories:
                    # we have a match!

                    aed_mice_category = None
                    # get our human readable category
                    for key, value in AED_APRS_MAPPING.items():
                        if value == mtype:
                            aed_mice_category = key
                            break

                    # get the remaining values from the message
                    mice_lat = mice_lon = mice_from = None
                    mice_speed = mice_course = None
                    if "latitude" in raw_aprs_packet:
                        mice_lat = round(raw_aprs_packet["latitude"], 6)
                    if "longitude" in raw_aprs_packet:
                        mice_lon = round(raw_aprs_packet["longitude"], 6)
                    if "from" in raw_aprs_packet:
                        mice_from = raw_aprs_packet["from"]
                    if "speed" in raw_aprs_packet:
                        mice_speed = round(raw_aprs_packet["speed"], 1)
                    if "course" in raw_aprs_packet:
                        mice_course = raw_aprs_packet["course"]

                    # and generate the Apprise message(s), dependent on how many
                    # config files the user has specified
                    #
                    # this is the "full message" branch which includes images
                    #
                    if aed_messenger_configfile:
                        generate_apprise_message(
                            apprise_config_file=aed_messenger_configfile,
                            callsign=mice_from,
                            latitude_aprs=mice_lat,
                            longitude_aprs=mice_lon,
                            latitude_aed=aed_latitude,
                            longitude_aed=aed_longitude,
                            course=mice_course,
                            speed=mice_speed,
                            category=aed_mice_category,
                            abbreviated_message_format=False,
                        )

                    # and this is the branch where we only send an abbreviated message to the user
                    if aed_sms_messenger_configfile:
                        generate_apprise_message(
                            apprise_config_file=aed_sms_messenger_configfile,
                            callsign=mice_from,
                            latitude=mice_lat,
                            longitude=mice_lon,
                            course=mice_course,
                            speed=mice_speed,
                            category=aed_mice_category,
                            abbreviated_message_format=True,
                        )

                    logger.info(raw_aprs_packet)


### main loop
###
if __name__ == "__main__":
    # get the command line params
    (
        aed_configfile,
        aed_messenger_configfile,
        aed_sms_messenger_configfile,
        aed_time_to_live,
        aed_generate_test_message,
    ) = get_command_line_params()

    # and then get the static config from our configuration file
    success, aed_mice_message_types, aed_latitude, aed_longitude, range_detection = (
        get_program_config_from_file(config_filename=aed_configfile)
    )
    if not success:
        sys.exit(0)

    # Determine the categories that we need to investigate
    aed_categories = []
    for aed_mice_message_type in aed_mice_message_types:
        if aed_mice_message_type in AED_APRS_MAPPING:
            aed_categories.append(AED_APRS_MAPPING[aed_mice_message_type])

    # Register the SIGTERM handler; this will allow a safe shutdown of the program
    logger.info(msg="Registering SIGTERM handler for safe shutdown...")
    signal.signal(signal.SIGTERM, signal_term_handler)

    # set up the expiring dict
    message_cache = ExpiringDict(
        max_len=APRS_TTL_MAX_MESSAGES, max_age_seconds=aed_time_to_live
    )

    # amend the APRS-IS filter in case we have received lat/lon/range
    if aed_latitude and aed_longitude and range_detection:
        aprsis_filter += f" r/{aed_latitude}/{aed_longitude}/{range_detection}"

    # and enter our eternal loop
    try:
        while True:
            AIS = aprslib.IS(aprsis_callsign, aprsis_passcode)
            AIS.set_server(aprsis_server_name, aprsis_server_port)
            AIS.set_filter(aprsis_filter)
            logger.info(
                msg=f"Trying to establish connection to APRS_IS: server={aprsis_server_name},"
                f"port={aprsis_server_port},filter={aprsis_filter},"
                f"APRS-IS User: {aprsis_callsign}, APRS-IS passcode: {aprsis_passcode}"
            )

            AIS.connect(blocking=True)
            if AIS._connected == True:
                logger.info(msg="Established the connection to APRS_IS")
                logger.info(msg="Starting callback consumer")
                AIS.consumer(mycallback, blocking=True, immortal=True, raw=False)
                logger.info("Have left the callback")
                logger.info(msg="Closing APRS connection to APRS_IS")
                AIS.close()
                time.sleep(10)
            else:
                logger.info(msg="Cannot re-establish connection to APRS_IS")
                time.sleep(10)

    except (KeyboardInterrupt, SystemExit):
        logger.info("received exception!")
        if AIS:
            AIS.close()
            logger.info(msg="Closed APRS connection to APRS_IS")
