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
import_rpl test.
"""
from __future__ import print_function
from __future__ import absolute_import

from builtins import range
import os

from . import copy_db_rpl

from mysql.utilities.exception import MUTLibError


_RPL_FILE = "rpl_test_import.txt"
_TEST_CASE_RESULTS = [
    # util result, db check results before, db check results after as follows:
    # BEFORE:
    #   SHOW DATABASES LIKE 'util_test'
    #   SELECT COUNT(*) FROM util_test.t1
    #   SHOW DATABASES LIKE 'master_db1'
    #   SELECT COUNT(*) FROM master_db1.t1
    # AFTER:
    #   SHOW DATABASES LIKE 'util_test'
    #   SELECT COUNT(*) FROM util_test.t1
    #   SHOW DATABASES LIKE 'master_db1'
    #   SELECT COUNT(*) FROM master_db1.t1
    #   <insert 2 rows into master_db1.t1>
    #   SELECT COUNT(*) FROM master_db1.t1
    [0, 0, 'util_test', '7', None, False, 'util_test', '7', 'master_db1', '3',
     '5'],
    [0, 0, 'util_test', '7', None, False, 'util_test', '7', 'master_db1', '5',
     '7'],
    [0, 0, 'util_test', '7', None, False, 'util_test', '7', 'master_db1', '7',
     '9'],
    [0, 0, 'util_test', '7', None, False, 'util_test', '7', 'master_db1', '9',
     '11'],
    [0, 0, 'util_test', '7', None, False, 'util_test', '7', 'master_db1', '11',
     '13'],
    [0, 0, None, False, None, False, 'util_test', '7', 'master_db1', '13',
     '15'],
    [0, 0, None, False, None, False, 'util_test', '7', 'master_db1', '15',
     '17'],
    [0, 0, None, False, None, False, 'util_test', '7', 'master_db1', '17',
     '17'],
    [0, 0, None, False, None, False, 'util_test', '7', 'master_db1', '19',
     '21'],
]

_FORMATS = ['sql', 'csv', 'tab', 'vertical', 'grid']

_EXPORT_CMD = ("mysqldbexport.py --export=both --format={0} "
               "--rpl-user=rpl:rpl --skip=events,grants,procedures,"
               "functions,views --rpl={1} {2} {3} {4} > {5}")

_IMPORT_CMD = "mysqldbimport.py {0} {1} --import=both --format={2} {3}"


class test(copy_db_rpl.test):
    """test export-to-import with replication features
    This test executes the replication feature in mysqldbexport via
    mysqldbimport to sync a slave and to test provisioning a slave from either
    a master or a slave. It uses the copy_db_rpl test as a parent for testing
    methods.
    """

    # Test Cases:
    #    - copy extra db on master
    #      do once for each format
    #    - provision a new slave from master
    #    - provision a new slave from existing slave

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 6, 5):
            raise MUTLibError("Test requires server version prior to 5.6.5")

        return copy_db_rpl.test.check_prerequisites(self)

    def setup(self):
        self.res_fname = "result.txt"
        return copy_db_rpl.test.setup(self)

    def run(self):
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        # TODO : make a test for '--skip-rpl'

        # Copy master database
        test_num = 1
        db_list = ["master_db1"]
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server2))
        for exp_fmt in _FORMATS:
            cmd_list = []
            comment = ("Test case {0} - Copy extra database from master to "
                       "slave - format =".format(test_num))

            exp_cmd = _EXPORT_CMD.format(exp_fmt, "master", " ".join(db_list),
                                         from_conn, "", _RPL_FILE)
            cmd_list.append(exp_cmd)

            imp_str = _IMPORT_CMD.format(to_conn, _RPL_FILE, exp_fmt, "")
            cmd_list.append(imp_str)

            res = self.run_test_case(0, test_num, self.server1, self.server1,
                                     self.server2, cmd_list, db_list,
                                     "", comment + exp_fmt, _TEST_CASE_RESULTS,
                                     True)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))
            test_num += 1

        # Provision a new slave from master
        to_conn = "--server={0}".format(
            self.build_connection_string(self.server3))
        db_list = ["util_test", "master_db1"]
        cmd_list = []
        exp_cmd = _EXPORT_CMD.format("sql", "master", " ".join(db_list),
                                     from_conn, "", _RPL_FILE)
        cmd_list.append(exp_cmd)

        imp_str = _IMPORT_CMD.format(to_conn, _RPL_FILE, "sql", "")
        cmd_list.append(imp_str)

        comment = ("Test case {0} - Provision a new slave from the "
                   "master".format(test_num))
        res = self.run_test_case(0, test_num, self.server1, self.server1,
                                 self.server3, cmd_list, db_list,
                                 "", comment + " sql", _TEST_CASE_RESULTS,
                                 True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Provision a new slave from existing slave
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server2))
        cmd_list = []
        exp_cmd = _EXPORT_CMD.format("sql", "slave", " ".join(db_list),
                                     from_conn, "", _RPL_FILE)
        cmd_list.append(exp_cmd)

        imp_str = _IMPORT_CMD.format(to_conn, _RPL_FILE, "sql", "")
        cmd_list.append(imp_str)

        comment = ("Test case {0} - Provision a new slave from existing "
                   "slave".format(test_num))
        res = self.run_test_case(0, test_num, self.server1, self.server2,
                                 self.server3, cmd_list, db_list,
                                 "", comment + " sql", _TEST_CASE_RESULTS,
                                 True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Now show the --skip-rpl effects
        # New rows will not appear in row count because the CM and START
        # commands are skipped.
        self.server3.exec_query("STOP SLAVE")
        self.server3.exec_query("DROP DATABASE util_test")
        self.server3.exec_query("DROP DATABASE master_db1")

        cmd_list = []
        exp_cmd = _EXPORT_CMD.format("sql", "slave", " ".join(db_list),
                                     from_conn, "", _RPL_FILE)
        cmd_list.append(exp_cmd)

        imp_str = _IMPORT_CMD.format(to_conn, _RPL_FILE, "sql",
                                     " --skip-rpl ")
        cmd_list.append(imp_str)

        comment = "Test case {0} - Use --skip-rpl on import".format(test_num)
        res = self.run_test_case(0, test_num, self.server1, self.server2,
                                 self.server3, cmd_list, db_list,
                                 "", comment + " sql", _TEST_CASE_RESULTS,
                                 False, True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        test_num += 1

        # Rollback here to avoid active transaction error for STOP SLAVE with
        # 5.5 servers.
        if self.servers.get_server(0).check_version_compat(5, 5, 0):
            self.server3.rollback()
        # Do the last test case again but don't skip to show rows are updated
        self.server3.exec_query("STOP SLAVE")
        self.server3.exec_query("RESET SLAVE")
        self.server3.exec_query("DROP DATABASE util_test")
        self.server3.exec_query("DROP DATABASE master_db1")

        cmd_list = []
        exp_cmd = _EXPORT_CMD.format("sql", "slave", " ".join(db_list),
                                     from_conn, "", _RPL_FILE)
        cmd_list.append(exp_cmd)

        imp_str = _IMPORT_CMD.format(to_conn, _RPL_FILE, "sql", " --skip-rpl ")
        cmd_list.append(imp_str)

        comment = "Test case {0} - Use --skip-rpl on import".format(test_num)
        res = self.run_test_case(0, test_num, self.server1, self.server2,
                                 self.server3, cmd_list, db_list,
                                 "", comment + " sql", _TEST_CASE_RESULTS,
                                 True)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        return True

    def get_result(self):
        # Here we check the result from execution of each test case.
        for i in range(0, len(_TEST_CASE_RESULTS)):
            if self.debug:
                print("  Actual results:", self.results[i][1:])
                print("Expected results:", _TEST_CASE_RESULTS[i])
            if self.results[i][1:] != _TEST_CASE_RESULTS[i]:
                msg = ("\n{0}\n  Actual result = {1}\nExpected result = "
                       "{2}\n".format(self.results[i][0], self.results[i][1:],
                                      _TEST_CASE_RESULTS[i]))
                return False, msg

        return True, ''

    def record(self):
        return True  # Not a comparative test

    def cleanup(self):
        try:
            os.unlink(_RPL_FILE)
        except OSError:
            pass
        return copy_db_rpl.test.cleanup(self)
