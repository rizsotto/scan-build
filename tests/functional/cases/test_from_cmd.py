# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
from . import make_args, check_call_and_report
import unittest

import os
import os.path
import glob


class OutputDirectoryTest(unittest.TestCase):

    @staticmethod
    def run_analyzer(outdir, args, cmd):
        return check_call_and_report(
            ['scan-build', '--intercept-first', '-o', outdir] + args,
            cmd)

    def test_regular_keeps_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_regular']
            outdir = self.run_analyzer(tmpdir, [], make)
            self.assertTrue(os.path.isdir(outdir))

    def test_clear_deletes_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_clean']
            outdir = self.run_analyzer(tmpdir, [], make)
            self.assertFalse(os.path.isdir(outdir))

    def test_clear_keeps_report_dir_when_asked(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_clean']
            outdir = self.run_analyzer(tmpdir, ['--keep-empty'], make)
            self.assertTrue(os.path.isdir(outdir))


class RunAnalyzerTest(unittest.TestCase):

    @staticmethod
    def get_plist_count(directory):
        return len(glob.glob(os.path.join(directory, 'report-*.plist')))

    def test_interposition_works(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_regular']
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--override-compiler'],
                make)

            self.assertTrue(os.path.isdir(outdir))
            self.assertEqual(self.get_plist_count(outdir), 5)

    def test_intercept_wrapper_works(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_regular']
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--intercept-first',
                 '--override-compiler'],
                make)

            self.assertTrue(os.path.isdir(outdir))
            self.assertEqual(self.get_plist_count(outdir), 5)

    def test_intercept_library_works(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_regular']
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--intercept-first'],
                make)

            self.assertTrue(os.path.isdir(outdir))
            self.assertEqual(self.get_plist_count(outdir), 5)

    def test_interposition_cc_works(self):
        with fixtures.TempDir() as tmpdir:
            filename = os.path.join(tmpdir, 'test.c')
            os.mknod(filename)
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--override-compiler'],
                ['sh', '-c', '$CC -c {0}'.format(filename)])
            self.assertEqual(self.get_plist_count(outdir), 1)

    def test_interposition_cxx_works(self):
        with fixtures.TempDir() as tmpdir:
            filename = os.path.join(tmpdir, 'test.c++')
            os.mknod(filename)
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--override-compiler'],
                ['sh', '-c', '$CXX -c {0}'.format(filename)])
            self.assertEqual(self.get_plist_count(outdir), 1)

    def test_intercept_cc_works(self):
        with fixtures.TempDir() as tmpdir:
            filename = os.path.join(tmpdir, 'test.c')
            os.mknod(filename)
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--override-compiler',
                 '--intercept-first'],
                ['sh', '-c', '$CC -c {0}'.format(filename)])
            self.assertEqual(self.get_plist_count(outdir), 1)

    def test_intercept_cxx_works(self):
        with fixtures.TempDir() as tmpdir:
            filename = os.path.join(tmpdir, 'test.c++')
            os.mknod(filename)
            outdir = check_call_and_report(
                ['scan-build', '--plist', '-o', tmpdir, '--override-compiler',
                 '--intercept-first'],
                ['sh', '-c', '$CXX -c {0}'.format(filename)])
            self.assertEqual(self.get_plist_count(outdir), 1)
