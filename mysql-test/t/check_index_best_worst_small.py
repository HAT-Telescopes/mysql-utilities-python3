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
check_index_best_worst_small test.
"""
from __future__ import absolute_import

import check_index_parameters

from mysql.utilities.exception import MUTLibError


class test(check_index_parameters.test):
    """check for best and worst indexes for the check_index_parameters utility
    This test executes the check index utility parameters on a single server.
    It uses the check_index_parameters test as a parent for setup and
    teardown methods.
    """

    def check_prerequisites(self):
        res = check_index_parameters.test.check_prerequisites(self)
        return res

    def setup(self):
        return check_index_parameters.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"
        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = "mysqlindexcheck.py {0} util_test_a ".format(from_conn)

        test_num = 1
        comment = ("Test case {0} - show best indexes on small "
                   "database".format(test_num))
        res = self.run_test_case(0, cmd_str + "--stats -v --best=5", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - show worst indexes on small "
                   "database".format(test_num))
        res = self.run_test_case(0, cmd_str + "--stats -v --worst=5", comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return check_index_parameters.test.cleanup(self)
