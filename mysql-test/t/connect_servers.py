#
# Copyright (c) 2010, 2014, Oracle and/or its affiliates. All rights reserved.
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
connect_servers test.
"""
from __future__ import print_function

from builtins import zip
from builtins import range
import mutlib

from mysql.utilities.exception import UtilError, FormatError
from mysql.utilities.common.server import connect_servers


class test(mutlib.System_test):
    """check connection_values()
    This test attempts to use the connect_servers method for using multiple
    parameter types for connection (dictionary, connection string, class).
    """

    server0 = None
    connect_str = None
    connect_dict = None
    test_cases = None

    def check_prerequisites(self):
        return self.check_num_servers(1)

    def setup(self):
        # We need a Server instance, a dictionary list, and a connection string
        self.server0 = self.servers.get_server(0)
        self.connect_str = self.build_connection_string(self.server0)
        self.connect_dict = self.servers.get_connection_values(self.server0)

        # list of tuples (comment, src, dest, result, fail)
        self.test_cases = [
            ('Server and Server', self.server0, self.server0,
             None, False),
            ('Server and Dictionary', self.server0,
             self.connect_dict, None, False),
            ('Server and String', self.server0,
             self.connect_str, None, False),
            ('Dictionary and String', self.connect_dict,
             self.connect_str, None, False),
            ('Dictionary and Server', self.connect_dict,
             self.server0, None, False),
            ('String and Server', self.connect_str,
             self.server0, None, False),
            ('String and Dictionary', self.connect_str,
             self.connect_dict, None, False),
            # Include at least one Failure to show that it
            # does still fail
            ('Bad String and Server', 'DAS*!@#MASD&UKKLKDA)!@#',
             self.server0, "Connection 'DAS*!@#MASD"
                           "&UKKLKDA)!@#' cannot be parsed as "
                           "a connection",
             True),
        ]
        return True

    def run(self):
        server_options = {'quiet': True, 'version': None,
                          'src_name': "test 1", 'dest_name': "test 2", }
        # Test mixes of the valid parameter types for server
        for i, test_case in enumerate(self.test_cases):
            try:
                connect_servers(test_case[1], test_case[2], server_options)
            except UtilError as err:
                self.results.append((test_case[0], True, err.errmsg))
            except FormatError as err:
                self.results.append((test_case[0], True, err))
            else:
                self.results.append((test_case[0], False, None))

        if self.debug:
            print("\nTest Results (test case, actual result, expected result):")
            for i in range(0, len(self.test_cases)):
                # pylint: disable=W0631
                print("{0}, {1}, {2}".format(
                    self.results[i][0], self.results[i][2], test_case[3]))

        return True

    def get_result(self):
        # Make sure we have enough results
        if len(self.results) != len(self.test_cases):
            return False, "Invalid number of test case results."

        # Check results to make sure test case completes as expected
        for test_case, result in zip(self.test_cases, self.results):
            if test_case[4] != result[1]:
                return False, result[2]

        return True, None

    def record(self):
        return True

    def cleanup(self):
        return True
