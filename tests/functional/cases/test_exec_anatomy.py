# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
import unittest

import os.path
import subprocess
import json


def run(target_dir):
    this_dir, _ = os.path.split(__file__)
    test_executable = os.path.join(target_dir, 'exec_anatomy')
    result_file = os.path.join(target_dir, 'result.json')
    expected_file = os.path.join(target_dir, 'expected.json')
    subprocess.check_call(
        ['bear', '--cdb', result_file, test_executable, expected_file],
        cwd=target_dir)
    return (expected_file, result_file)


class OutputDirectoryTest(unittest.TestCase):

    def assertEqualJson(self, expected, result):
        def read_json(filename):
            with open(filename) as handler:
                return json.load(handler)

        lhs = read_json(expected)
        rhs = read_json(result)
        for item in lhs:
            self.assertTrue(rhs.count(item))
        for item in rhs:
            self.assertTrue(lhs.count(item))

    @unittest.skip("running exec_anatomy from build dir shall be implemented")
    def test_regular_keeps_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            expected, result = run(tmpdir)
            self.assertEqualJson(expected, result)
