# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
#
# RUN: %{python} %s

import libear
import libscanbuild.intercept as sut
import unittest
import tempfile
import os.path


class InterceptUtilTest(unittest.TestCase):

    def test_read_write_exec_trace(self):
        input_one = {
            'pid': 123,
            'ppid': 121,
            'function': 'wrapper',  # it's a constant in the parse method
            'directory': '/path/to/here',
            'command': ['cc', '-c', 'this.c']
        }
        input_two = {
            'pid': 124,
            'ppid': 121,
            'function': 'wrapper',  # it's a constant in the parse method
            'directory': '/path/to/here',
            'command': ['cc', '-c', 'that.c']
        }
        # test with a single exec report
        with tempfile.NamedTemporaryFile() as temp_file:
            sut.write_exec_trace(temp_file.name, **input_one)
            result = sut.parse_exec_trace(temp_file.name)
            self.assertEqual([input_one], list(result))
        # test with multiple exec report
        with tempfile.NamedTemporaryFile() as temp_file:
            sut.write_exec_trace(temp_file.name, **input_one)
            sut.write_exec_trace(temp_file.name, **input_two)
            result = sut.parse_exec_trace(temp_file.name)
            self.assertEqual([input_one, input_two], list(result))

    def test_format_entry_filters_action(self):
        def test(command):
            trace = {'command': command, 'directory': '/opt/src/project'}
            return list(sut.format_entry(trace))

        self.assertTrue(test(['cc', '-c', 'file.c', '-o', 'file.o']))
        self.assertFalse(test(['cc', '-E', 'file.c']))
        self.assertFalse(test(['cc', '-MM', 'file.c']))
        self.assertFalse(test(['cc', 'this.o', 'that.o', '-o', 'a.out']))

    def test_format_entry_normalize_filename(self):
        parent = os.path.join(os.sep, 'home', 'me')
        current = os.path.join(parent, 'project')

        def test(filename):
            trace = {'directory': current, 'command': ['cc', '-c', filename]}
            return list(sut.format_entry(trace))[0]['file']

        self.assertEqual(os.path.join(current, 'file.c'), test('file.c'))
        self.assertEqual(os.path.join(current, 'file.c'), test('./file.c'))
        self.assertEqual(os.path.join(parent, 'file.c'), test('../file.c'))
        self.assertEqual(os.path.join(current, 'file.c'),
                         test(os.path.join(current, 'file.c')))

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
