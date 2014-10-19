# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.runner as sut
from . import fixtures
import unittest
import re
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


class SetAnalyzerOutputTest(fixtures.TestCase):

    def test_html(self):
        with fixtures.TempDir() as tmpdir:
            opts = {'out_dir': tmpdir, 'output_format': 'html'}
            spy = fixtures.Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['output'][1]))
            self.assertTrue(os.path.isdir(spy.arg['output'][1]))

    def test_plist_html(self):
        with fixtures.TempDir() as tmpdir:
            opts = {'out_dir': tmpdir, 'output_format': 'plist-html'}
            spy = fixtures.Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['output'][1]))
            self.assertTrue(os.path.isfile(spy.arg['output'][1]))

    def test_plist(self):
        with fixtures.TempDir() as tmpdir:
            opts = {'out_dir': tmpdir, 'output_format': 'plist'}
            spy = fixtures.Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['output'][1]))
            self.assertTrue(os.path.isfile(spy.arg['output'][1]))


class ReportFailureTest(fixtures.TestCase):

    def assertUnderFailures(self, path):
        self.assertEqual('failures', os.path.basename(os.path.dirname(path)))

    def test_report_failure_create_files(self):
        with fixtures.TempDir() as tmpdir:
            # create input file
            filename = os.path.join(tmpdir, 'test.c')
            with open(filename, 'w') as handle:
                handle.write('int main() { return 0')
            uname_msg = ' '.join(os.uname()) + os.linesep
            error_msg = 'this is my error output'
            # execute test
            opts = {'directory': os.getcwd(),
                    'file': filename,
                    'report': ['clang', '-fsyntax-only', '-E', filename],
                    'language': 'c',
                    'out_dir': tmpdir,
                    'error_type': 'other_error',
                    'error_output': error_msg,
                    'exit_code': 13}
            sut.report_failure(opts)
            # verify the result
            result = dict()
            pp_file = None
            for root, _, files in os.walk(tmpdir):
                keys = [os.path.join(root, name) for name in files]
                for key in keys:
                    with open(key, 'r') as handle:
                        result[key] = handle.readlines()
                    if re.match(r'^(.*/)+clang(.*)\.i$', key):
                        pp_file = key

            # prepocessor file generated
            self.assertUnderFailures(pp_file)
            # info file generated and content dumped
            info_file = pp_file + '.info.txt'
            self.assertIn(info_file, result)
            self.assertEqual('Other Error\n', result[info_file][1])
            self.assertEqual(uname_msg, result[info_file][3])
            # error file generated and content dumped
            error_file = pp_file + '.stderr.txt'
            self.assertIn(error_file, result)
            self.assertEqual([error_msg], result[error_file])
