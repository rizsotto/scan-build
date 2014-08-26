# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.beye as sut
import tests.fixtures as fixtures
import unittest
import os
import os.path


def run_bug_scan(content):
    with fixtures.TempDir() as tmpdir:
        file_name = tmpdir + os.sep + 'test.html'
        with open(file_name, 'w') as fd:
            fd.writelines(content)
        return sut.scan_bug(file_name)


def run_crash_scan(content, preproc):
    with fixtures.TempDir() as tmpdir:
        file_name = tmpdir + os.sep + preproc + '.info.txt'
        with open(file_name, 'w') as fd:
            fd.writelines(content)
        return sut.scan_crash(file_name)


class ScanFileTest(unittest.TestCase):

    def test_scan_bug(self):
        content = [
            "some header\n",
            "<!-- BUGDESC Division by zero -->\n",
            "<!-- BUGTYPE Division by zero -->\n",
            "<!-- BUGCATEGORY Logic error -->\n",
            "<!-- BUGFILE xx -->\n",
            "<!-- BUGLINE 5 -->\n",
            "<!-- BUGCOLUMN 22 -->\n",
            "<!-- BUGPATHLENGTH 4 -->\n",
            "<!-- BUGMETAEND -->\n",
            "<!-- REPORTHEADER -->\n",
            "some tails\n"]
        result = run_bug_scan(content)
        self.assertEqual(result['bug_category'], 'Logic error')
        self.assertEqual(result['bug_path_length'], 4)
        self.assertEqual(result['bug_line'], 5)
        self.assertEqual(result['bug_description'], 'Division by zero')
        self.assertEqual(result['bug_type'], 'Division by zero')
        self.assertEqual(result['bug_file'], 'xx')
        self.assertEqual(result['bug_type_class'],
                         'bt_logic_error_division_by_zero')

    def test_scan_bug_empty(self):
        content = []
        result = run_bug_scan(content)
        self.assertEqual(result['bug_category'], 'Other')
        self.assertEqual(result['bug_path_length'], 1)
        self.assertEqual(result['bug_line'], 0)
        self.assertEqual(result['bug_type_class'], 'bt_other_')

    def test_scan_crash(self):
        content = [
            "/some/path/file.c\n",
            "Some very serious Error\n",
            "bla\n",
            "bla-bla\n"]
        result = run_crash_scan(content, 'file.i')
        self.assertEqual(result['source'], content[0].rstrip())
        self.assertEqual(result['problem'], content[1].rstrip())
        self.assertEqual(os.path.basename(result['preproc']),
                         'file.i')
        self.assertEqual(os.path.basename(result['stderr']),
                         'file.i.stderr.txt')

    def test_scan_real_crash(self):
        import analyzer.driver as sut2
        import re
        with fixtures.TempDir() as tmpdir:
            # create input file
            with open(tmpdir + os.sep + 'test.c', 'w') as fd:
                fd.write('int main() { return 0')
            # produce failure report
            opts = {'language': 'c',
                    'directory': tmpdir,
                    'file': 'test.c',
                    'clang': 'clang',
                    'uname': 'this and that\n',
                    'html_dir': tmpdir,
                    'error_type': 'other_error',
                    'error_output': 'some output',
                    'exit_code': 13}
            sut2.report_failure(opts, lambda x: x)
            # find the info file
            pp_file = None
            for root, _, files in os.walk(tmpdir):
                keys = [os.path.join(root, name) for name in files]
                for key in keys:
                    if re.match('^(.*/)+clang(.*)\.i$', key):
                        pp_file = key
            self.assertIsNot(pp_file, None)
            # read the failure report back
            result = sut.scan_crash(pp_file + '.info.txt')
            self.assertEqual(os.path.basename(result['source']), 'test.c')
            self.assertEqual(result['problem'], 'Other Error')
            self.assertEqual(result['preproc'], pp_file)
            self.assertEqual(result['stderr'], pp_file + '.stderr.txt')
