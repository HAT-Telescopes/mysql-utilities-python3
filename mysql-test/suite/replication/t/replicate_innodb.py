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
replicate_innodb test.
"""
from __future__ import absolute_import

import os

from . import replicate

from mysql.utilities.exception import MUTLibError, UtilError


class test(replicate.test):
    """setup replication
    This test attempts to replicate among a master and slave whose
    innodb settings are different. It uses the replicate test for
    inherited methods.
    """

    server5 = None
    s5_serverid = None

    def check_prerequisites(self):
        if self.servers.get_server(0).check_version_compat(5, 5, 0):
            raise MUTLibError("Test requires server version 5.1.")
        return self.check_num_servers(1)

    def setup(self):
        self.server0 = self.servers.get_server(0)
        self.server5 = None
        self.s5_serverid = None

        replicate.test.setup(self)

        index = self.servers.find_server_by_name("rep_slave_no_innodb")
        if index >= 0:
            self.server5 = self.servers.get_server(index)
            try:
                res = self.server5.show_server_variable("server_id")
            except MUTLibError as err:
                raise MUTLibError("Cannot get replication slave "
                                  "server_id: {0}".format(err.errmsg))
            self.s5_serverid = int(res[0][1])
        else:
            self.s5_serverid = self.servers.get_next_id()
            res = self.servers.spawn_new_server(
                self.server0, self.s5_serverid, "rep_slave_no_innodb",
                ' --mysqld="--log-bin=mysql-bin  --skip-innodb '
                '--default-storage-engine=MyISAM"')
            if not res:
                raise MUTLibError("Cannot spawn replication slave server.")
            self.server5 = res[0]
            self.servers.add_new_server(self.server5, True)

        return True

    # pylint: disable=W0221
    def run_test_case(self, slave, master, s_id,
                      comment, options=None, expected_result=0):
        master_str = "--master={0}".format(
            self.build_connection_string(master))
        slave_str = " --slave={0}".format(
            self.build_connection_string(slave))
        conn_str = master_str + slave_str

        # Test case 1 - setup replication among two servers
        self.results.append(comment + "\n")
        cmd = "mysqlreplicate.py -vvv --rpl-user=rpl:rpl {0}".format(conn_str)
        if options:
            cmd += " {0}".format(options)
        res = self.exec_util(cmd, self.res_fname)
        self.record_results(self.res_fname)
        if res != expected_result:
            return False

        return True

    def run(self):
        self.res_fname = "result.txt"

        test_num = 1
        comment = "Test case {0} - show warnings if innodb different".format(
            test_num)
        res = self.run_test_case(self.server5, self.server2, self.s5_serverid,
                                 comment, None)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        test_num += 1
        comment = ("Test case {0} - use pedantic to fail if innodb "
                   "different".format(test_num))
        res = self.run_test_case(self.server5, self.server2, self.s5_serverid,
                                 comment, " --pedantic", 1)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        try:
            self.server5.exec_query("STOP SLAVE")
        except UtilError:
            raise MUTLibError("{0}: Failed to stop slave.".format(comment))

        replicate.test.mask_results(self)

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return True
