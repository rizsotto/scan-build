# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
from . import make_args, check_call_and_report
import unittest

import os.path


class OutputDirectoryTest(unittest.TestCase):
    @staticmethod
    def run_sb(outdir, args, cmd):
        return check_call_and_report(
            ['scan-build', '--intercept-first', '-o', outdir] + args,
            cmd)

    def test_regular_keeps_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_regular']
            outdir = self.run_sb(tmpdir, [], make)
            self.assertTrue(os.path.isdir(outdir))

    def test_clear_deletes_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_clean']
            outdir = self.run_sb(tmpdir, [], make)
            self.assertFalse(os.path.isdir(outdir))

    def test_clear_keeps_report_dir_when_asked(self):
        with fixtures.TempDir() as tmpdir:
            make = make_args(tmpdir) + ['build_clean']
            outdir = self.run_sb(tmpdir, ['--keep-empty'], make)
            self.assertTrue(os.path.isdir(outdir))
