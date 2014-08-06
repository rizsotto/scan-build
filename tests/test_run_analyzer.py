# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.driver as sut
import tests.fixtures as fixtures
import unittest
import os


def run_analyzer(content, opts):
    with fixtures.TempDir() as tmpdir:
        with open(tmpdir + os.sep + 'test.cpp', 'w') as fd:
            fd.write(content)
        adds = {'language': 'c++',
                'directory': tmpdir,
                'file': 'test.cpp',
                'clang': 'clang'}
        spy = fixtures.Spy()
        result = sut.run_analyzer(
            sut.filter_dict(opts, frozenset(), adds), spy.call)
        return (result, spy.arg)


class RunAnalyzerTest(unittest.TestCase):

    def test_run_analyzer(self):
        content = "int div(int n, int d) { return n / d; }"
        (result, fwds) = run_analyzer(content, dict())
        self.assertEquals(None, fwds)
        self.assertEquals(0, result)

    def test_run_analyzer_crash(self):
        content = "int div(int n, int d) { return n / d }"
        (result, fwds) = run_analyzer(content, dict())
        self.assertEquals(None, fwds)
        self.assertEquals(1, result)

    def test_run_analyzer_crash_and_forwarded(self):
        content = "int div(int n, int d) { return n / d }"
        (result, fwds) = run_analyzer(content, {'report_failures': True})
        self.assertEquals('crash', fwds['error_type'])
        self.assertEquals(1, fwds['exit_code'])
        self.assertTrue(len(fwds['error_output']) > 0)
