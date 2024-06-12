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
APRS_OFF_DUTY = "M0: Off Duty"
APRS_EN_ROUTE = "M1: En Route"
APRS_IN_SERVICE = "M2: In Service"
APRS_RETURNING = "M3: Returning"
APRS_COMMITTED = "M4: Committed"
APRS_SPECIAL = "M5: Special"
APRS_PRIORITY = "M6: Priority"
APRS_EMERGENCY = "Emergency"

# These are the APRS message types that we actually want to search for
AED_MESSAGE_TYPES = (APRS_EMERGENCY, APRS_PRIORITY)

# TTL value for messages in hours
# If we detect the same message content within this time span, we will
# ignore the message UNLESS content such as position data et al changes
APRS_TTL = 4

# Max number of APRS TTL entries
APRS_TTL_MAX_MESSAGES = 1000

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)


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


def mycallback(raw_aprs_packet):
    # Unfortunately, APRS-IS does not offer a filter
    # for Mic-E messages. Therefore, we have to filter
    # these messages ourselves
    if "format" in raw_aprs_packet:
        fmt = raw_aprs_packet["format"]
        if fmt == "mic-e":
            if "mtype" in raw_aprs_packet:
                mtype = raw_aprs_packet["mtype"]
                if mtype in AED_MESSAGE_TYPES:
                    logger.info(raw_aprs_packet)


### main loop
###
if __name__ == "__main__":
    # Register the SIGTERM handler; this will allow a safe shutdown of the program
    logger.info(msg="Registering SIGTERM handler for safe shutdown...")
    signal.signal(signal.SIGTERM, signal_term_handler)

    message_cache = ExpiringDict(
        max_len=APRS_TTL_MAX_MESSAGES, max_age_seconds=60 * APRS_TTL
    )

    try:
        while True:
            AIS = aprslib.IS(aprsis_callsign, aprsis_passcode)
            AIS.set_server(aprsis_server_name, aprsis_server_port)
            AIS.set_filter(aprsis_filter)
            logger.info(
                msg=f"Establish connection to APRS_IS: server={aprsis_server_name},"
                f"port={aprsis_server_port},filter={aprsis_filter}"
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
