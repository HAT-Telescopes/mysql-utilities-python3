#
# Copyright (c) 2010, 2016, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

"""
This file contains grep processing.
"""
from __future__ import print_function

from builtins import str
from builtins import range
from builtins import object
import re
import sys

import mysql.connector

from mysql.utilities.exception import EmptyResultError, FormatError
from mysql.utilities.common.format import print_list
from mysql.utilities.common.ip_parser import parse_connection
from mysql.utilities.common.options import obj2sql
from mysql.utilities.common.server import set_ssl_opts_in_connection_info


KILL_QUERY, KILL_CONNECTION, PRINT_PROCESS = list(range(3))

ID = "ID"
USER = "USER"
HOST = "HOST"
DB = "DB"
COMMAND = "COMMAND"
TIME = "TIME"
STATE = "STATE"
INFO = "INFO"


#
# TODO : Can _spec and similar methods be shared for grep.py?
#
def _spec(info):
    """Create a server specification string from an info structure.
    """
    result = "{user}:*@{host}:{port}".format(**info)
    if "unix_socket" in info:
        result += ":" + info["unix_socket"]
    return result

_SELECT_PROC_FRM = """
SELECT
  Id, User, Host, Db, Command, Time, State, Info
FROM
  INFORMATION_SCHEMA.PROCESSLIST{condition}"""


def _make_select(matches, use_regexp, conditions):
    """Generate a SELECT statement for matching the processes.
    """
    oper = 'REGEXP' if use_regexp else 'LIKE'
    for field, pattern in matches:
        conditions.append("    {0} {1} {2}"
                          "".format(field, oper, obj2sql(pattern)))
    if len(conditions) > 0:
        condition = "\nWHERE\n" + "\n  AND\n".join(conditions)
    else:
        condition = ""
    return _SELECT_PROC_FRM.format(condition=condition)

# Map to map single-letter suffixes number of seconds
_SECS = {'s': 1, 'm': 60, 'h': 3600, 'd': 24 * 3600, 'w': 7 * 24 * 3600}

_INCORRECT_FORMAT_MSG = "'{0}' does not have correct format"


def _make_age_cond(age):
    """Make age condition

    Accept an age description return a timedelta representing the age.  We
    allow the forms: hh:mm:ss, mm:ss, 4h3m, with suffixes d (days), w (weeks),
    h (hours), m (minutes), and s(seconds)

    age[in]            Age (time)

    Returns string - time delta
    """
    mobj = re.match(r"([+-])?(?:(?:(\d?\d):)?(\d?\d):)?(\d?\d)\Z", age)
    if mobj:
        sign, hrs, mins, secs = mobj.groups()
        if not hrs:
            hrs = 0
        if not mins:
            mins = 0
        seconds = int(secs) + 60 * (int(mins) + 60 * int(hrs))
        oper = "<=" if sign and sign == "-" else ">="
        return '    {0} {1} {2}'.format(TIME, oper, seconds)
    mobj = re.match(r"([+-])?(\d+[dwhms])+", age)
    if mobj:
        sign = None
        if mobj.group(1):
            sign = age[0]
            age = age[1:]
        seconds = 0
        periods = [x for x in re.split(r"(\d+[dwhms])", age)]
        if len(''.join(x[0::2])) > 0:  # pylint: disable=W0631
            raise FormatError(_INCORRECT_FORMAT_MSG.format(age))
        for period in periods[1::2]:
            seconds += int(period[0:-1]) * _SECS[period[-1:]]
        oper = "<=" if sign and sign == "-" else ">="
        return '    {0} {1} {2}'.format(TIME, oper, seconds)
    raise FormatError(_INCORRECT_FORMAT_MSG.format(age))

_KILL_BODY = """
DECLARE kill_done INT;
DECLARE kill_cursor CURSOR FOR
  {select}
OPEN kill_cursor;
BEGIN
   DECLARE id BIGINT;
   DECLARE EXIT HANDLER FOR NOT FOUND SET kill_done = 1;
   kill_loop: LOOP
      FETCH kill_cursor INTO id;
      KILL {kill} id;
   END LOOP kill_loop;
END;
CLOSE kill_cursor;"""

_KILL_PROCEDURE = """
CREATE PROCEDURE {name} ()
BEGIN{body}
END"""


class ProcessGrep(object):
    """Grep processing
    """

    def __init__(self, matches, actions=None, use_regexp=False, age=None):
        """Constructor

        matches[in]    matches identified
        actions[in]    actions to perform
        use_regexp[in] if True, use regexp for compare
                       default = False
        age[in]        age in time, if provided
                       default = None
        """
        if actions is None:
            actions = []
        conds = [_make_age_cond(age)] if age else []
        self.__select = _make_select(matches, use_regexp, conds).strip()
        self.__actions = actions

    def sql(self, only_body=False):
        """Generate a SQL command for KILL

        This method generates the KILL <id> SQL command for killing processes.
        It can also generate SQL to kill procedures by recreating them without
        a body (if only_body = True).

        only_body[in]  if True, limit to body of object
                       default = False

        Returns string - SQL statement
        """
        params = {
            'select': "\n      ".join(self.__select.split("\n")),
            'kill': 'CONNECTION' if KILL_CONNECTION in self.__actions
                    else 'QUERY',
        }
        if KILL_CONNECTION in self.__actions or KILL_QUERY in self.__actions:
            sql = _KILL_BODY.format(**params)
            if not only_body:
                sql = _KILL_PROCEDURE.format(
                    name="kill_processes",
                    body="\n   ".join(sql.split("\n"))
                )
            return sql
        else:
            return self.__select

    def execute(self, connections, **kwrds):
        """Execute the search for processes, queries, or connections

        This method searches for processes, queriers, or connections to
        either kill or display the matches for one or more servers.

        connections[in]    list of connection parameters
        kwrds[in]          dictionary of options
          output           file stream to display information
                           default = sys.stdout
          connector        connector to use
                           default = mysql.connector
          format           format for display
                           default = GRID
        """

        output = kwrds.get('output', sys.stdout)
        connector = kwrds.get('connector', mysql.connector)
        fmt = kwrds.get('format', "grid")
        charset = kwrds.get('charset', None)
        ssl_opts = kwrds.get('ssl_opts', {})

        print_opts = {
            'none_to_zls'  : (fmt.lower() == 'csv'),
            'none_to_null' : (fmt.lower() == 'sql'),
        }

        headers = ("Connection", "Id", "User", "Host", "Db",
                   "Command", "Time", "State", "Info")
        entries = []
        # Build SQL statement
        for info in connections:
            conn = parse_connection(info)
            if not conn:
                msg = "'%s' is not a valid connection specifier" % (info,)
                raise FormatError(msg)
            if charset:
                conn['charset'] = charset
            info = conn

            if connector == mysql.connector:
                set_ssl_opts_in_connection_info(ssl_opts, info)

            connection = connector.connect(**info)

            if not charset:
                # If no charset provided, get it from the
                # "character_set_client" server variable.
                cursor = connection.cursor()
                cursor.execute("SHOW VARIABLES LIKE 'character_set_client'")
                res = cursor.fetchall()
                connection.set_charset_collation(charset=str(res[0][1]))
                cursor.close()

            cursor = connection.cursor()
            cursor.execute(self.__select)
            print_rows = []
            cols = ["Id", "User", "Host", "db", "Command", "Time",
                    "State", "Info"]
            for row in cursor:
                if (KILL_QUERY in self.__actions) or \
                   (KILL_CONNECTION in self.__actions):
                    print_rows.append(row)
                    cursor.execute("KILL {0}".format(row[0]))
                if PRINT_PROCESS in self.__actions:
                    entries.append(tuple([_spec(info)] + list(row)))
            if print_rows:
                print("# The following KILL commands were executed:")
                print_list(output, fmt, cols, print_rows,
                           print_opt = print_opts)

        # If output is None, nothing is printed
        if len(entries) > 0 and output:
            entries.sort(key=lambda fifth: fifth[5])
            print_list(output, fmt, headers, entries,
                       print_opt = print_opts)
        elif PRINT_PROCESS in self.__actions:
            raise EmptyResultError("No matches found")
