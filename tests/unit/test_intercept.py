# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
# RUN: %{python} %s

import os
import os.path
import unittest

import libear
import libscanbuild.intercept as sut
from libscanbuild import Execution

IS_WINDOWS = os.getenv('windows')


class InterceptUtilTest(unittest.TestCase):

    def test_read_write_exec_trace(self):
        input_one = Execution(
            pid=123,
            cwd='/path/to/here',
            cmd=['cc', '-c', 'this.c'])
        with libear.temporary_directory() as tmp_dir:
            temp_file = os.path.join(tmp_dir, 'single_report.cmd')
            sut.write_exec_trace(temp_file, input_one)
            result = sut.parse_exec_trace(temp_file)
            self.assertEqual(input_one, result)

    @unittest.skipIf(IS_WINDOWS, 'this code is not running on windows')
    def test_sip(self):
        def create_status_report(filename, message):
            content = """#!/usr/bin/env sh
                         echo 'sa-la-la-la'
                         echo 'la-la-la'
                         echo '{0}'
                         echo 'sa-la-la-la'
                         echo 'la-la-la'
                      """.format(message)
            lines = [line.strip() for line in content.split(os.linesep)]
            with open(filename, 'w') as handle:
                handle.write(os.linesep.join(lines))
                handle.close()
            os.chmod(filename, 0x1ff)

        def create_csrutil(dest_dir, status):
            filename = os.path.join(dest_dir, 'csrutil')
            message = 'System Integrity Protection status: {0}'.format(status)
            return create_status_report(filename, message)

        enabled = 'enabled'
        disabled = 'disabled'
        osx = 'darwin'

        saved = os.environ['PATH']
        with libear.temporary_directory() as tmp_dir:
            try:
                os.environ['PATH'] = os.pathsep.join([tmp_dir, saved])

                create_csrutil(tmp_dir, enabled)
                self.assertTrue(sut.is_preload_disabled(osx))

                create_csrutil(tmp_dir, disabled)
                self.assertFalse(sut.is_preload_disabled(osx))
            finally:
                os.environ['PATH'] = saved

        try:
            os.environ['PATH'] = ''
            # shall be false when it's not in the path
            self.assertFalse(sut.is_preload_disabled(osx))

            self.assertFalse(sut.is_preload_disabled('unix'))
        finally:
            os.environ['PATH'] = saved


if __name__ == '__main__':
    unittest.main()
