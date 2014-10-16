# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
import unittest

import os.path
import subprocess


def run_bear(result, args):
    this_dir, _ = os.path.split(__file__)
    path = os.path.normpath(os.path.join(this_dir, '..', 'src', 'build'))
    child = subprocess.Popen(['bear', '--cdb', result] + args,
                             universal_newlines=True,
                             cwd=path,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    output = child.stdout.readlines()
    child.stdout.close()
    child.wait()
    return (child.returncode, output)


class CompilationDatabaseTest(unittest.TestCase):

    def test_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            run_bear(result, ['make', 'regular'])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                import json
                content = json.load(handler)
                self.assertEqual(5, len(content))

    def test_not_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            run_bear(result, ['make', 'broken'])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                import json
                content = json.load(handler)
                self.assertEqual(2, len(content))


class ExitCodeTest(unittest.TestCase):

    def test_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            exit_code, _ = run_bear(result, ['make', 'regular'])
            self.assertFalse(exit_code)

    def test_not_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            exit_code, _ = run_bear(result, ['make', 'broken'])
            self.assertTrue(exit_code)
