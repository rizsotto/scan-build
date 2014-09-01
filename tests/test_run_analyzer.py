# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.driver as sut
import tests.fixtures as fixtures
import unittest
import os
import os.path


def run_analyzer(content, opts):
    with fixtures.TempDir() as tmpdir:
        filename = os.path.join(tmpdir, 'test.cpp')
        with open(filename, 'w') as handle:
            handle.write(content)

        opts.update({
            'directory': os.getcwd(),
            'file': filename,
            'language': 'c++',
            'analyze': ['clang', '--analyze', '-x', 'c++', filename],
            'output': ['-o', tmpdir]})
        spy = fixtures.Spy()
        result = sut.run_analyzer(opts, spy.call)
        return (result, spy.arg)


class RunAnalyzerTest(unittest.TestCase):

    def test_run_analyzer(self):
        content = "int div(int n, int d) { return n / d; }"
        (result, fwds) = run_analyzer(content, dict())
        self.assertEqual(None, fwds)
        self.assertEqual(0, result['exit_code'])

    def test_run_analyzer_crash(self):
        content = "int div(int n, int d) { return n / d }"
        (result, fwds) = run_analyzer(content, dict())
        self.assertEqual(None, fwds)
        self.assertEqual(1, result['exit_code'])

    def test_run_analyzer_crash_and_forwarded(self):
        content = "int div(int n, int d) { return n / d }"
        (_, fwds) = run_analyzer(content, {'report_failures': True})
        self.assertEqual('crash', fwds['error_type'])
        self.assertEqual(1, fwds['exit_code'])
        self.assertTrue(len(fwds['error_output']) > 0)
