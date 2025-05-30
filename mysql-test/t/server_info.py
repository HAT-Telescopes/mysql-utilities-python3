#
# Copyright (c) 2010, 2015, Oracle and/or its affiliates. All rights reserved.
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
server_info test.
"""

import os
import time

import mutlib

from mysql.utilities.exception import MUTLibError


class test(mutlib.System_test):
    """simple db serverinfo
    This test executes the serverinfo utility.
    """

    server1 = None
    server2 = None
    server3 = None
    need_server = False
    res_fname_temp = None
    basedir = None
    datadir3 = None

    def check_prerequisites(self):
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: {0}".format(
                    err.errmsg))
        self.server2 = self.servers.get_server(1)
        return True

    def do_replacements(self):
        """Mask out this information to make result file deterministic.
        """
        self.replace_result("                  version:",
                            "                  version: XXXX\n")
        self.replace_result("                  datadir:",
                            "                  datadir: XXXX\n")
        self.replace_result("                  basedir:",
                            "                  basedir: XXXX\n")
        self.replace_result("               plugin_dir:",
                            "               plugin_dir: XXXX\n")
        self.replace_result("              config_file:",
                            "              config_file: XXXX\n")
        self.replace_result("               binary_log:",
                            "               binary_log: XXXX\n")
        self.replace_result("           binary_log_pos:",
                            "           binary_log_pos: XXXX\n")
        self.replace_result("                relay_log:",
                            "                relay_log: XXXX\n")
        self.replace_result("            relay_log_pos:",
                            "            relay_log_pos: XXXX\n")
        self.replace_result("                   server: localhost:",
                            "                   server: localhost: XXXX\n")
        self.replace_result("                   server: socket:",
                            "                   server: socket: XXXX\n")        
        self.replace_result("              general_log:",
                            "              general_log: XXXX\n")
        self.replace_result("         general_log_file:",
                            "         general_log_file: XXXX\n")
        self.replace_result("    general_log_file_size:",
                            "    general_log_file_size: XXXX\n")
        self.replace_result("                log_error:",
                            "                log_error: XXXX\n")
        self.replace_result("      log_error_file_size:",
                            "      log_error_file_size: XXXX\n")
        self.replace_result("           slow_query_log:",
                            "           slow_query_log: XXXX\n")
        self.replace_result("      slow_query_log_file:",
                            "      slow_query_log_file: XXXX\n")
        self.replace_result(" slow_query_log_file_size:",
                            " slow_query_log_file_size: XXXX\n")
        # Remove warning that appears only on 5.7 and which is not important
        # for the sake of this test.
        self.remove_result_and_lines_around(
            "WARNING: Unable to get size information from 'stderr' "
            "for 'error log'.", lines_before=3, lines_after=1)
        self.remove_result("# Warning: cannot get server version")
        self.replace_result("# Source on socket:",
                            "# Source on socket: XXXX ... connected.\n")
        
    def start_stop_newserver(self, delete_log=True, stop_server=True):
        """Start and stop new server.

        delete_log[in]    True for delete log.
        stop_server[in]   True for stop server.
        """
        port = int(self.servers.get_next_port())
        res = self.servers.start_new_server(self.server1, port,
                                            self.servers.get_next_id(), "root",
                                            "temp_server_info")
        self.server3 = res[0]
        if not self.server3:
            raise MUTLibError("Failed to create a new slave.")

        from_conn3 = "--server={0}".format(
            self.build_connection_string(self.server3))
        cmd_str = "mysqlserverinfo.py {0} ".format(from_conn3)

        # Now, stop the server then run verbose test again
        res = self.server3.show_server_variable('basedir')
        self.basedir = os.path.normpath(res[0][1])
        res = self.server3.show_server_variable('datadir')
        self.datadir3 = os.path.normpath(res[0][1])
        if stop_server:
            self.servers.stop_server(self.server3, 12, False)
        if delete_log:
            self.remove_logs_from_server(self.datadir3)
        self.servers.remove_server(self.server3.role)
        return cmd_str

    @staticmethod
    def remove_logs_from_server(datadir):
        """Removes logs from server.

        datadir[in]   Data dir.
        """
        # restarting server fails if log is different, from the original
        # so we will delete them.
        logs = ["ib_logfile0", "ib_logfile1"]
        while logs:
            for log in tuple(logs):
                log_file = os.path.join(datadir, log)
                if os.path.exists(log_file):
                    try:
                        os.unlink(log_file)
                        time.sleep(1)
                        if not os.path.exists(log_file):
                            logs.remove(log)
                    except OSError:
                        pass

    def run(self):
        self.mask_global = False  # Turn off global masks
        quote_char = "'" if os.name == "posix" else '"'
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        s2_conn = "--server={0}".format(
            self.build_connection_string(self.server2))

        cmd_str = "mysqlserverinfo.py {0} ".format(s2_conn)

        test_num = 1
        comment = "Test case {0} - basic serverinfo ".format(test_num)
        cmd_opts = " --format=vertical "
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))
        self.results.append("\n")
        self.do_replacements()

        # NOTICE: Cannot test the -d option with a comparative result file
        #         because it is going to be different on every machine.
        #         Thus, this test case will have to be checked independently.

        self.res_fname_temp = "result2.txt"

        test_num += 1
        comment = "Test case {0} - basic serverinfo with -d option".format(
            test_num)
        self.results.append(comment + '\n')
        cmd_opts = " --format=vertical -d "

        try:
            res = self.exec_util(cmd_str + cmd_opts, self.res_fname_temp)
        except MUTLibError as err:
            raise MUTLibError(err.errmsg)
        if res != 0:
            return False
        self.results.append("\n")

        cmd_str = self.start_stop_newserver()
        test_num += 1
        cmd_opts = (' --format=vertical --basedir={2}{0}{2} --datadir={2}{1}'
                    '{2} --start'.format(self.basedir, self.datadir3,
                                         quote_char))
        comment = ("Test case {0} - re-started server prints "
                   "results ".format(test_num))
        # cmd_str_wrong = cmd_str.replace("root:root", "wrong:wrong")
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("{0}: failed".format(comment))

        time.sleep(2)
        self.do_replacements()
        return True

    def get_result(self):
        # First, check result of test case 2
        found = False
        with open(self.res_fname_temp, 'r') as f:
            for line in f:
                if line[0:19] == "Defaults for server":
                    found = True
                    break
        if self.res_fname_temp:
            os.unlink(self.res_fname_temp)
        if not found:
            raise MUTLibError("Test Case 2 failed. No defaults found.")
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        if self.res_fname:
            try:
                os.unlink(self.res_fname)
            except OSError:
                pass
        from mysql.utilities.common.tools import delete_directory

        if self.server3:
            delete_directory(self.datadir3)
            self.server3 = None
        return True
