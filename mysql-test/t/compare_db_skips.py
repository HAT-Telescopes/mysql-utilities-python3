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
compare_db_skips test.
"""
from __future__ import absolute_import

import compare_db

from mysql.utilities.exception import MUTLibError

_SKIPS = ['object-compare', 'row-count', 'diff', 'checksum-table',
          'data-check']


class test(compare_db.test):
    """check skip parameters for dbcompare
    This test executes a series of check database operations on two
    servers using a variety of skip parameters. It uses the compare_db test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        return compare_db.test.check_prerequisites(self)

    def setup(self, spawn_servers=True):
        return compare_db.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        s1_conn = "--server1={0}".format(
            self.build_connection_string(self.server1))
        s2_conn = "--server2={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = "mysqldbcompare.py {0} {1} inventory:inventory ".format(
            s1_conn, s2_conn)

        compare_db.test.alter_data(self)

        skip_all = ""
        test_num = 0
        for skip in _SKIPS:
            test_num += 1
            skip_all = skip_all + " --skip-" + skip
            cmd_opts = " --skip-%s --format=csv -t" % skip
            comment = "Test case %d - %s " % (test_num, cmd_opts)
            res = self.run_test_case(1, cmd_str + cmd_opts, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        cmd_opts = " %s --format=csv -t" % skip_all
        comment = "Test case %d - %s " % (test_num, cmd_opts)
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        compare_db.test.do_replacements(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return compare_db.test.cleanup(self)
