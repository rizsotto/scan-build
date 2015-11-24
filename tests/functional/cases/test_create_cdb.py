# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
from . import make_args, silent_check_call, silent_call
import unittest

import os.path
import json


class CompilationDatabaseTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, args):
        result = os.path.join(tmpdir, 'cdb.json')
        make = make_args(tmpdir) + args
        silent_check_call(
            ['intercept-build', '--cdb', result] + make)
        return result

    def test_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, ['build_regular'])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(5, len(content))

    def test_successful_build_with_wrapper(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            make = make_args(tmpdir) + ['build_regular']
            silent_check_call(['intercept-build', '--cdb', result,
                               '--override-compiler'] + make)
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(5, len(content))

    @unittest.skipIf(os.getenv('TRAVIS'), 'ubuntu make return -11')
    def test_successful_build_parallel(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, ['-j', 'build_regular'])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(5, len(content))

    @unittest.skipIf(os.getenv('TRAVIS'), 'ubuntu env remove clang from path')
    def test_successful_build_on_empty_env(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            make = make_args(tmpdir) + ['CC=clang', 'build_regular']
            silent_check_call(['intercept-build', '--cdb', result,
                               'env', '-'] + make)
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(5, len(content))

    def test_successful_build_all_in_one(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, ['-j', 'build_all_in_one'])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(3, len(content))

    def test_not_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            result = os.path.join(tmpdir, 'cdb.json')
            make = make_args(tmpdir) + ['build_broken']
            silent_call(
                ['intercept-build', '--cdb', result] + make)
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(2, len(content))


class ExitCodeTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, target):
        result = os.path.join(tmpdir, 'cdb.json')
        make = make_args(tmpdir) + [target]
        return silent_call(
            ['intercept-build', '--cdb', result] + make)

    def test_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            exitcode = self.run_intercept(tmpdir, 'build_clean')
            self.assertFalse(exitcode)

    def test_not_successful_build(self):
        with fixtures.TempDir() as tmpdir:
            exitcode = self.run_intercept(tmpdir, 'build_broken')
            self.assertTrue(exitcode)


class ResumeFeatureTest(unittest.TestCase):
    @staticmethod
    def run_intercept(tmpdir, target, args):
        result = os.path.join(tmpdir, 'cdb.json')
        make = make_args(tmpdir) + [target]
        silent_check_call(
            ['intercept-build', '--cdb', result] + args + make)
        return result

    def test_overwrite_existing_cdb(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, 'build_clean', [])
            self.assertTrue(os.path.isfile(result))
            result = self.run_intercept(tmpdir, 'build_regular', [])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(2, len(content))

    def test_append_to_existing_cdb(self):
        with fixtures.TempDir() as tmpdir:
            result = self.run_intercept(tmpdir, 'build_clean', [])
            self.assertTrue(os.path.isfile(result))
            result = self.run_intercept(tmpdir, 'build_regular', ['--append'])
            self.assertTrue(os.path.isfile(result))
            with open(result, 'r') as handler:
                content = json.load(handler)
                self.assertEqual(5, len(content))
