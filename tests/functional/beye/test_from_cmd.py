# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
import unittest

import os.path
import subprocess


def run_sb(target_dir, args):
    this_dir, _ = os.path.split(__file__)
    path = os.path.normpath(os.path.join(this_dir, '..', 'src', 'build'))
    child = subprocess.Popen(['scan-build', '-o', target_dir] + args,
                             universal_newlines=True,
                             cwd=path,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    output = child.stdout.readlines()
    child.stdout.close()
    child.wait()
    return (child.returncode, output)


class OutputDirectoryTest(unittest.TestCase):

    def test_regular_keeps_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            outdir = os.path.join(tmpdir, 'result')
            run_sb(outdir, ['make', 'regular'])
            self.assertTrue(os.path.isdir(outdir))

    def test_clear_deletes_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            outdir = os.path.join(tmpdir, 'result')
            run_sb(outdir, ['make', 'clean'])
            self.assertFalse(os.path.isdir(outdir))

    def test_clear_keeps_report_dir_when_asked(self):
        with fixtures.TempDir() as tmpdir:
            outdir = os.path.join(tmpdir, 'result')
            run_sb(outdir, ['--keep-empty', 'make', 'clean'])
            self.assertTrue(os.path.isdir(outdir))
