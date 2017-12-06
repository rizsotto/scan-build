# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

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

    def test_expand_cmd_with_response_files(self):
        with libear.temporary_directory() as tmp_dir:
            response_file = os.path.join(tmp_dir, 'response.jom')
            with open(response_file, 'w') as response_file_handle:
                response_file_handle.write('        Hello\n')
                response_file_handle.write('        World!\n')
            cmd_input = ['echo', '@'+response_file]
            cmd_output = ['echo', 'Hello', 'World!']
            self.assertEqual(cmd_output,
                             sut.expand_cmd_with_response_files(cmd_input))

    def test_write_exec_trace_with_response(self):
        with libear.temporary_directory() as tmp_dir:
            response_file_one = os.path.join(tmp_dir, 'response1.jom')
            response_file_two = os.path.join(tmp_dir, 'response2.jom')
            input_one = Execution(
                pid=123,
                cwd='/path/to/here',
                cmd=['clang-cl', '-c', '@'+response_file_one,
                     '-Idoes_not_exists', '@'+response_file_two])
            output_one = Execution(
                pid=123,
                cwd='/path/to/here',
                cmd=['clang-cl', '-c', '-DSOMETHING_HERE',
                     '-Idoes_not_exists', 'that.cpp'])
            with open(response_file_one, 'w') as response_file_one_handle:
                response_file_one_handle.write('        -DSOMETHING_HERE\n')
            with open(response_file_two, 'w') as response_file_two_handle:
                response_file_two_handle.write('        that.cpp\n')

            temp_file = os.path.join(tmp_dir, 'single_report.cmd')
            sut.write_exec_trace(temp_file, input_one)
            result = sut.parse_exec_trace(temp_file)
            self.assertEqual(output_one, result)

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
