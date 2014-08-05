# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.core as sut
import tests.fixtures as fixtures
import unittest
import os


def run_scan(content):
    with fixtures.TempDir() as tmpdir:
        file_name = tmpdir + os.sep + 'test.html'
        with open(file_name, 'w') as fd:
            fd.writelines(content)
        opts = {'output_file': file_name}
        spy = fixtures.Spy()
        return (sut.scan_file(opts, spy.call), spy.arg)


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
        (result, fwds) = run_scan(content)
        self.assertEqual(0, result)
        self.assertEqual(fwds['bug_category'], 'Logic error')
        self.assertEqual(fwds['bug_path_length'], 4)
        self.assertEqual(fwds['bug_line'], 5)
        self.assertEqual(fwds['bug_description'], 'Division by zero')
        self.assertEqual(fwds['bug_type'], 'Division by zero')
        self.assertEqual(fwds['bug_file'], 'xx')

    def test_scan_file_empty(self):
        content = []
        (result, fwds) = run_scan(content)
        self.assertEqual(0, result)
        self.assertEqual(fwds['bug_category'], 'Other')
        self.assertEqual(fwds['bug_path_length'], 1)
        self.assertEqual(fwds['bug_line'], 0)
