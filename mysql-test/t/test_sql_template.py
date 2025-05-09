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
test_sql_template test.
"""
from __future__ import print_function

from builtins import range
import os
import sys

import mutlib

from mysql.utilities.exception import MUTLibError
from mysql.utilities.common.tools import get_tool_path


_TRANSFORM_FILE = "diff_output.txt"

_CREATE_DB = "CREATE DATABASE `{0}`"

_TEST_CASES = [
    # Direction a->b
    {'run_util': True,  # If true, run utility
     'options': " --difftype=sql --changes-for=server1 > "
                "{0}".format(_TRANSFORM_FILE),
     'comment': "Test case {0} changes-for = server1 : {1}",
     # If true, run startup commands, load data and create objects
     'load_data': True, 'exp_result': 1, },
    # Do consume test (specified in run() method below)
    {'run_util': False,  # If true, run utility
     'comment': "Test case {0} consume transformation information : {1}",
     'run_on': 'server1', 'load_data': False, 'exp_result': 0, },
    # Check to ensure compliance of transformation
    {'run_util': True,  # If true, run utility
     'options': " --difftype=sql --changes-for=server1 ",
     'comment': "Test case {0} changes-for = server1 post transform : {1}",
     'load_data': False, 'exp_result': 0, },  # Direction a<-b
    {'run_util': True,  # If true, run utility
     'options': " --difftype=sql --changes-for=server2 > "
                "{0}".format(_TRANSFORM_FILE),
     'comment': "Test case {0} changes-for = server2 : {1}",
     'load_data': True,  # If true, load the data and create objects
     'exp_result': 1, },
    # Do consume test (specified in run() method below)
    {'run_util': False,  # If true, run utility
     'comment': "Test case {0} consume transformation information : {1}",
     'run_on': 'server2', 'load_data': False, 'exp_result': 0, },
    # Check to ensure compliance of transformation
    {'run_util': True,  # If true, run utility
     'options': " --difftype=sql --changes-for=server2 ",
     'comment': "Test case {0} changes-for = server2 post transform : {1}",
     'load_data': False, 'exp_result': 0, },
    # Direction a<->b with dir = a
    {'run_util': True,  # If true, run utility
     'options': " --difftype=sql --changes-for=server1 "
                "--show-reverse ",
     'comment': "Test case {0} changes-for = server1 with reverse : {1}",
     'load_data': True,  # If true, load the data and create objects
     'exp_result': 1, },  # Direction a<->b with dir = b
    {'run_util': True,  # If true, run utility
     'options': " --difftype=sql --changes-for=server2 "
                "--show-reverse ",
     'comment': "Test case {0} changes-for = server2 with reverse : {1}",
     'load_data': True,  # If true, load the data and create objects
     'exp_result': 1, },
]


class test(mutlib.System_test):
    """Template for diff_<object>_sql tests
    This test executes a set of test cases for a given object definition pair.
    It is a value result test.

    The pair is stored as list of dictionary items in the following format:

        test_object = {
            'db1'             : <name of first database>,
            'db2'             : <name of second database>,
            'object_name'     : <name of object>,
            'server1_object'  : <create statement for first server>,
            'server2_object'  : <create statement for second server>,
            'comment'         : <comment to be appended to test case name>,
            'startup_cmds'    : <array of commands to execute before test
            case>,
            'shutdown_cmds'   : <array of commands to execute after test case>,
            # OPTIONAL - use for error code checking
            'error_codes'     : <array of 7 integers used for checking errors>,
                                # default = 1,0,0,1,0,0,1,1
            # OPTIONAL - use for loading data (e.g. INSERT INTO)
            'server1_data'    : <array of insert commands for server1>
            'server2_data'    : <array of insert commands for server2>
        }
        self.test_objects.append(test_object)

    For item in the dictionary of test objects, the following test cases are
    executed:

        - operation generated with --difftype=sql option, changes-for=server1
        - SQL consumed
        - operation rerun and check result against 'expected_result'
        - operation generated with --difftype=sql option, changes-for=server2
        - SQL consumed
        - operation rerun and check result against 'expected_result'
        - operation generated with --difftype=sql option,
          changes-for=server1 with show-reverse
        - operation generated with --difftype=sql option,
          changes-for=server2 with show-reverse

    To specify a new test object, do so in the setup method as described above
    and call the template setup method. You can add multiple object pairs to
    the list self.test_objects so that you can test different variants of the
    CREATE statement to check for the various mechanisms of how diff generates
    the SQL statements.

    Note: the expected result for all test cases is 1 (errors found). It
          shall be considered an error if this returns 0. Similarly, all
          consumption runs is expected to generate a result of 0 and any other
          value is considered an error.

    You must supply the utility name via self.utility. Set it to either
    'mysqldiff.py' for diff_sql* tests or 'mysqldbcompare.py' for
    db_compare_sql* tests. Set it in the setup *before* calling
    test_sql_template.test.setup().

    """

    server1 = None
    server2 = None
    need_server = False
    mysql_path = None
    base_cmd = None
    test_objects = None

    def check_prerequisites(self):
        # if self.servers.get_server(0).check_version_compat(5, 6, 5):
        #     raise MUTLibError("Test requires server version prior to 5
        # .6.5")
        self.test_objects = []

        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(3):
            self.need_server = True
        return True

    # pylint: disable=W0221
    def setup(self, spawn_servers=True):
        self.res_fname = "result.txt"
        if self.need_server:
            try:
                self.servers.spawn_new_servers(3)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers:"
                                  " {0}".format(err.errmsg))
        self.server1 = self.servers.get_server(1)
        self.server2 = self.servers.get_server(2)

        s1_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))
        s2_conn = "--server2={0}".format(
            self.build_connection_string(self.server2))

        # pylint: disable=E1101
        self.base_cmd = "{0} {1} {2} ".format(self.utility, s1_conn, s2_conn)

        rows = self.server1.exec_query("SHOW VARIABLES LIKE 'basedir'")
        if rows:
            basedir = rows[0][1]
        else:
            raise MUTLibError("Unable to determine basedir of running "
                              "server.")

        self.mysql_path = get_tool_path(basedir, "mysql", quote=True)

        return True

    def run(self):
        # Run the test cases for each object
        test_num = 1
        for obj in self.test_objects:
            obj['test_case_results'] = []
            for i in range(0, len(_TEST_CASES)):
                comment = _TEST_CASES[i]['comment'].format(test_num,
                                                           obj['comment'])

                if _TEST_CASES[i]['load_data']:
                    self._drop_all(obj)  # It's Ok if this fails
                    self.server1.exec_query(_CREATE_DB.format(obj['db1']))
                    self.server2.exec_query(_CREATE_DB.format(obj['db2']))

                if _TEST_CASES[i]['run_util']:

                    if _TEST_CASES[i]['load_data']:
                        # Run any startup commands listed
                        for cmd in obj['startup_cmds']:
                            self.server1.exec_query(cmd)
                            self.server2.exec_query(cmd)
                            # Create the objects
                        if obj['server1_object'] != '':
                            self.server1.exec_query(obj['server1_object'])
                        if obj['server2_object'] != '':
                            self.server2.exec_query(obj['server2_object'])

                        # Do data loads
                        for cmd in obj.get('server1_data', []):
                            self.server1.exec_query(cmd)
                        for cmd in obj.get('server2_data', []):
                            self.server2.exec_query(cmd)

                    if obj['object_name'] == "":  # we're testing whole dbs
                        cmd_opts = "{0}:{1} {2}".format(
                            obj['db1'], obj['db2'], _TEST_CASES[i]['options'])
                    else:
                        cmd_opts = "{0}.{1}:{2}.{3} {4}".format(
                            obj['db1'], obj['object_name'], obj['db2'],
                            obj['object_name'], _TEST_CASES[i]['options'])
                    res = self.run_test_case_result(self.base_cmd + cmd_opts,
                                                    comment)

                    if _TEST_CASES[i]['load_data']:
                        # Run any shutdown commands listed
                        for cmd in obj['shutdown_cmds']:
                            self.server1.exec_query(cmd)
                            self.server2.exec_query(cmd)

                else:
                    if self.debug:
                        print("\n{0}".format(comment))

                    if _TEST_CASES[i]['run_on'] == 'server1':
                        conn_val = self.get_connection_values(self.server1)
                    else:
                        conn_val = self.get_connection_values(self.server2)

                    command = "{0} -uroot ".format(self.mysql_path)
                    if conn_val[1] is not None and len(conn_val[1]) > 0:
                        command = "{0}-p{1} ".format(command, conn_val[1])
                    if conn_val[2] is not None and len(conn_val[2]) > 0:
                        if conn_val[2] != "localhost":
                            command = "{0}-h {1} ".format(command, conn_val[2])
                        else:
                            command = "{0}-h 127.0.0.1 ".format(command)
                        if ']' in conn_val[2]:
                            host = conn_val[2].replace('[', '')
                            host = host.replace(']', '')
                            command = "{0}-h {1} ".format(command, host)
                    if conn_val[3] is not None:
                        command = "{0}--port={1} ".format(command,
                                                          conn_val[3])
                    if conn_val[4] is not None:
                        command = "{0}--socket={1} ".format(command,
                                                            conn_val[4])
                    command = "{0} < {1}".format(command, _TRANSFORM_FILE)
                    res = self.exec_util(command, self.res_fname, True)

                    if self.debug:
                        # Display results of command in _TRANSFORM_FILE
                        # Note: flush not to mix output with utility
                        sys.stdout.flush()
                        if self.res_fname:
                            print("\nResult file:")
                            t_res = open(self.res_fname,'r+')
                            for line in t_res.readline():
                                print(line, end=' ')
                            t_res.close()
                            sys.stdout.flush()
                            os.unlink(self.res_fname)

                        
                        print("\nContents of output file:")
                        t_file = open(_TRANSFORM_FILE, 'r+')
                        for line in t_file.readlines():
                            print(line, end=' ')
                        t_file.close()
                        sys.stdout.flush()

                error_codes = obj.get('error_codes', None)
                if error_codes is not None and len(error_codes) >= i + 1:
                    exp_res = error_codes[i]
                else:
                    exp_res = _TEST_CASES[i]['exp_result']
                obj['test_case_results'].append((res, exp_res, comment))
                test_num += 1

        return True

    def get_result(self):
        # Here we check the result from execution of each test object.
        # We check all and show a list of those that failed.
        failed_object_tests = []
        for obj in self.test_objects:
            try:
                for result in obj['test_case_results']:
                    if result[0] != result[1]:
                        failed_object_tests.append(result)
            except (KeyError, IndexError):
                return (False, "No test results found for object test "
                               "diff {0} {1} comment: "
                               "{2}".format(obj['db1'], obj['db2'],
                                            obj['comment']))
        if len(failed_object_tests) > 0:
            msg = ""
            for result in failed_object_tests:
                msg = ("{0}\n{1}\nExpected result = {2}, actual result = "
                       "{3}.\n".format(msg, result[2], result[1], result[0]))
            return False, msg

        return True, ''

    def record(self):
        return True  # Not a comparative test

    def _drop_all(self, test_object):
        """Drops all databases created.
        """
        self.drop_db(self.server1, test_object["db1"])
        self.drop_db(self.server2, test_object["db2"])
        return True

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        os.unlink(_TRANSFORM_FILE)
        # Make sure all databases have been dropped. It is Ok if this fails.
        for obj in self.test_objects:
            self._drop_all(obj)
        return True
