# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from ...unit import fixtures
import unittest

import os.path
import string
import subprocess
import glob


def prepare_cdb(name, target_dir):
    target_file = 'build_{0}.json'.format(name)
    this_dir, _ = os.path.split(__file__)
    path = os.path.normpath(os.path.join(this_dir, '..', 'src'))
    source_dir = os.path.join(path, 'compilation_database')
    source_file = os.path.join(source_dir, target_file + '.in')
    target_file = os.path.join(target_dir, 'compile_commands.json')
    with open(source_file, 'r') as in_handle:
        with open(target_file, 'w') as out_handle:
            for line in in_handle:
                temp = string.Template(line)
                out_handle.write(temp.substitute(path=path))
    return target_file


def run_beye(directory, cdb, args):
    cmd = ['scan-build', 'analyze', '--cdb', cdb, '--output', directory] + args
    child = subprocess.Popen(cmd,
                             universal_newlines=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    output = child.stdout.readlines()
    child.stdout.close()
    child.wait()
    return (child.returncode, output)


class OutputDirectoryTest(unittest.TestCase):

    def test_regular_keeps_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertTrue(os.path.isdir(outdir))

    def test_clear_deletes_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('clean', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertFalse(os.path.isdir(outdir))

    def test_clear_keeps_report_dir_when_asked(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('clean', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, ['--keep-empty'])
            self.assertTrue(os.path.isdir(outdir))


class ExitCodeTest(unittest.TestCase):

    def test_regular_does_not_set_exit_code(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertFalse(exit_code)

    def test_clear_does_not_set_exit_code(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('clean', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertFalse(exit_code)

    def test_regular_sets_exit_code_if_asked(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, ['--status-bugs'])
            self.assertTrue(exit_code)

    def test_clear_does_not_set_exit_code_if_asked(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('clean', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, ['--status-bugs'])
            self.assertFalse(exit_code)

    def test_regular_sets_exit_code_if_asked_from_plist(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb,
                                         ['--status-bugs', '--plist'])
            self.assertTrue(exit_code)

    def test_clear_does_not_set_exit_code_if_asked_from_plist(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('clean', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb,
                                         ['--status-bugs', '--plist'])
            self.assertFalse(exit_code)


class OutputFormatTest(unittest.TestCase):

    @staticmethod
    def get_html_count(directory):
        return len(glob.glob(os.path.join(directory, 'report-*.html')))

    @staticmethod
    def get_plist_count(directory):
        return len(glob.glob(os.path.join(directory, 'report-*.plist')))

    def test_default_creates_html_report(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertTrue(os.path.exists(os.path.join(outdir, 'index.html')))
            self.assertEqual(self.get_html_count(outdir), 2)
            self.assertEqual(self.get_plist_count(outdir), 0)

    def test_plist_and_html_creates_html_report(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, ['--plist-html'])
            self.assertTrue(os.path.exists(os.path.join(outdir, 'index.html')))
            self.assertEqual(self.get_html_count(outdir), 2)
            self.assertEqual(self.get_plist_count(outdir), 5)

    def test_plist_does_not_creates_html_report(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('regular', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, ['--plist'])
            self.assertFalse(
                os.path.exists(os.path.join(outdir, 'index.html')))
            self.assertEqual(self.get_html_count(outdir), 0)
            self.assertEqual(self.get_plist_count(outdir), 5)


class FailureReportTest(unittest.TestCase):

    def test_broken_creates_failure_reports(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('broken', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertTrue(os.path.isdir(os.path.join(outdir, 'failures')))

    def test_broken_does_not_creates_failure_reports(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('broken', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, ['--no-failure-reports'])
            self.assertFalse(os.path.isdir(os.path.join(outdir, 'failures')))


class TitleTest(unittest.TestCase):

    def assertTitleEqual(self, directory, expected):
        import re
        patterns = [
            re.compile(r'<title>(?P<page>.*)</title>'),
            re.compile(r'<h1>(?P<head>.*)</h1>')]
        result = dict()

        index = os.path.join(directory, 'result', 'index.html')
        with open(index, 'r') as handler:
            for line in handler.readlines():
                for regex in patterns:
                    match = regex.match(line.strip())
                    if match:
                        result.update(match.groupdict())
                        break
        self.assertEqual(result['page'], result['head'])
        self.assertEqual(result['page'], expected)

    def test_default_title_in_report(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('broken', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb, [])
            self.assertTitleEqual(tmpdir, 'src - analyzer results')

    def test_given_title_in_report(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_cdb('broken', tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, cdb,
                                         ['--html-title', 'this is the title'])
            self.assertTitleEqual(tmpdir, 'this is the title')
