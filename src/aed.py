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
                mtype = raw_aprs_packet["mtype"]
                if mtype in aed_categories:
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
    success, aed_mice_message_types, latitude, longitude, range_detection = (
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
    if latitude and longitude and range_detection:
        aprsis_filter += f" r/{latitude}/{longitude}/{range_detection}"

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
