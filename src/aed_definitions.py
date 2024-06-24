#!/usr/bin/env python3
#
# APRS Emergency Detector: constant definitions
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

# APRS-IS communication parameters
# This program is only going to receive
# data; therefore, we do not need a passcode
aprsis_callsign = "N0CALL"
aprsis_passcode = "-1"
aprsis_server_name = "euro.aprs2.net"
aprsis_server_port = 14580
AIS = None
# filter value might get amended in case the user
# has specified a range value for APRS-IS monitoring
aprsis_filter = "t/p"

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
AED_MICE_TESTALARM = "TESTALARM"  # only used for APRS 1.2 extended messages

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

# APRS 1.2 Emergency extension for the msg body, see
# http://wa8lmf.net/bruninga/aprs/EmergencyCode.txt
# only used when enabled in the program's config file
APRS_EXTENDED_OFF_DUTY = "!OFF-DUTY!"
APRS_EXTENDED_EN_ROUTE = "!ENROUTE!"
APRS_EXTENDED_IN_SERVICE = "!INSERVICE!"
APRS_EXTENDED_RETURNING = "!RETURNING!"
APRS_EXTENDED_COMMITTED = "!COMMITTED!"
APRS_EXTENDED_SPECIAL = "!SPECIAL!"
APRS_EXTENDED_PRIORITY = "!PRIORITY!"
APRS_EXTENDED_EMERGENCY = "!EMERGENCY!"
APRS_EXTENDED_TESTALARM = "!TESTALARM!"

# APRS 1.2 Emergency extension for TOCALL, see
# http://wa8lmf.net/bruninga/aprs/EmergencyCode.txt
# only used when enabled in the program's config file
APRS_EXTENDED_TOCALL_ALARM = "ALARM"
APRS_EXTENDED_TOCALL_ALERT = "ALERT"
APRS_EXTENDED_TOCALL_WARNING = "WARNING"
APRS_EXTENDED_TOCALL_WXALARM = "WXALARM"
APRS_EXTENDED_TOCALL_EM = "EM"

# APRS 1.2 extension mapping - message body
AED_APRS_EXTENDED_MAPPING = {
    AED_MICE_OFF_DUTY: APRS_EXTENDED_OFF_DUTY,
    AED_MICE_EN_ROUTE: APRS_EXTENDED_EN_ROUTE,
    AED_MICE_IN_SERVICE: APRS_EXTENDED_IN_SERVICE,
    AED_MICE_RETURNING: APRS_EXTENDED_RETURNING,
    AED_MICE_COMMITTED: APRS_EXTENDED_COMMITTED,
    AED_MICE_SPECIAL: APRS_EXTENDED_SPECIAL,
    AED_MICE_PRIORITY: APRS_EXTENDED_PRIORITY,
    AED_MICE_EMERGENCY: APRS_EXTENDED_EMERGENCY,
    AED_MICE_TESTALARM: APRS_EXTENDED_TESTALARM,
}

# APRS 1.2 extension mapping - TOCALL
APRS_EXTENDED_TOCALL_LIST = [
    APRS_EXTENDED_TOCALL_ALARM,
    APRS_EXTENDED_TOCALL_ALERT,
    APRS_EXTENDED_TOCALL_WARNING,
    APRS_EXTENDED_TOCALL_WXALARM,
    APRS_EXTENDED_TOCALL_EM,
]


# Max number of APRS TTL entries for the
# ExpiringDict dictionary
APRS_TTL_MAX_MESSAGES = 1000

if __name__ == "__main__":
    pass
