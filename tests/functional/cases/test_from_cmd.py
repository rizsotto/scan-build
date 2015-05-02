# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
from . import make_args, silent_check_call
import unittest

import os.path


class OutputDirectoryTest(unittest.TestCase):

    @staticmethod
    def run_sb(outdir, args):
        return silent_check_call(['scan-build', 'all', '-o', outdir] + args)

    def test_regular_keeps_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            outdir = os.path.join(tmpdir, 'result')
            make = make_args(tmpdir) + ['build_regular']
            self.run_sb(outdir, make)
            self.assertTrue(os.path.isdir(outdir))

    def test_clear_deletes_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            outdir = os.path.join(tmpdir, 'result')
            make = make_args(tmpdir) + ['build_clean']
            self.run_sb(outdir, make)
            self.assertFalse(os.path.isdir(outdir))

    def test_clear_keeps_report_dir_when_asked(self):
        with fixtures.TempDir() as tmpdir:
            outdir = os.path.join(tmpdir, 'result')
            make = make_args(tmpdir) + ['build_clean']
            self.run_sb(outdir, ['--keep-empty'] + make)
            self.assertTrue(os.path.isdir(outdir))
