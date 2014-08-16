# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.report as sut
import tests.fixtures as fixtures
import unittest
import os


def run_scan(content):
    with fixtures.TempDir() as tmpdir:
        file_name = tmpdir + os.sep + 'test.html'
        with open(file_name, 'w') as fd:
            fd.writelines(content)
        return sut.scan_file(file_name)


class ScanFileTest(unittest.TestCase):

    def test_scan_file(self):
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
        result = run_scan(content)
        self.assertEqual(result['bug_category'], 'Logic error')
        self.assertEqual(result['bug_path_length'], 4)
        self.assertEqual(result['bug_line'], 5)
        self.assertEqual(result['bug_description'], 'Division by zero')
        self.assertEqual(result['bug_type'], 'Division by zero')
        self.assertEqual(result['bug_file'], 'xx')

    def test_scan_file_empty(self):
        content = []
        result = run_scan(content)
        self.assertEqual(result['bug_category'], 'Other')
        self.assertEqual(result['bug_path_length'], 1)
        self.assertEqual(result['bug_line'], 0)
