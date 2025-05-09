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
export_skip_objects test.
"""
from __future__ import absolute_import

import export_basic

from mysql.utilities.exception import MUTLibError


class test(export_basic.test):
    """check export db skips
    This test executes a series of export database operations using a variety
    of skip object parameters. It uses the export_basic test as a parent for
    setup and teardown methods.
    """

    def check_prerequisites(self):
        return export_basic.test.check_prerequisites(self)

    def setup(self, spawn_servers=True):
        return export_basic.test.setup(self)

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--server={0}".format(
            self.build_connection_string(self.server1))

        cmd_str = ("mysqldbexport.py {0} util_test --format=CSV "
                   "--display=NAMES --skip-gtid --skip=data".format(from_conn))

        test_num = 1
        comment = "Test case {0} - baseline".format(test_num)
        res = self.run_test_case(0, cmd_str, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        _SKIPS = [",grants", ",events", ",functions", ",procedures",
                  ",triggers", ",views", ",tables"]
        skip_str = ""
        for skip in _SKIPS:
            test_num += 1
            skip_str = "{0}{1}".format(skip_str, skip)
            cmd_opts = "{0}{1}".format(cmd_str, skip_str)
            comment = "Test case {0} - no data,{1}".format(test_num, skip_str)
            res = self.run_test_case(0, cmd_opts, comment)
            if not res:
                raise MUTLibError("{0}: failed".format(comment))

        self.replace_substring("on [::1]", "on localhost")

        self.remove_result("# WARNING: The server supports GTIDs")

        self.remove_result("'root'@'localhost',ALTER") 
        self.remove_result("'root'@'localhost',CREATE") 
        self.remove_result("'root'@'localhost',DELETE,") 
        self.remove_result("'root'@'localhost',DROP,") 
        self.remove_result("'root'@'localhost',EVENT,") 
        self.remove_result("'root'@'localhost',EXECUTE,") 
        self.remove_result("'root'@'localhost',INDEX,") 
        self.remove_result("'root'@'localhost',INSERT,") 
        self.remove_result("'root'@'localhost',LOCK ") 
        self.remove_result("'root'@'localhost',REFERENCES,") 
        self.remove_result("'root'@'localhost',SELECT,") 
        self.remove_result("'root'@'localhost',SHOW VIEW,") 
        self.remove_result("'root'@'localhost',TRIGGER,") 
        self.remove_result("'root'@'localhost',UPDATE,") 


        return True

    def get_result(self):
        return self.compare_pp(__name__, self.results,
                               self.server1)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        return export_basic.test.cleanup(self)
