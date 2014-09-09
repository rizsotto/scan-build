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


FILES = ['build_clean.json', 'build_regular.json', 'build_brokens.json']


def prepare_compilation_db(target_file_idx, target_dir):
    this_dir, _ = os.path.split(__file__)
    path = os.path.normpath(os.path.join(this_dir, '..', 'src'))
    source_dir = os.path.join(path, 'compilation_database')
    source_file = os.path.join(source_dir, FILES[target_file_idx] + '.in')
    target_file = os.path.join(target_dir, 'compile_commands.json')
    with open(source_file, 'r') as in_handle:
        with open(target_file, 'w') as out_handle:
            for line in in_handle:
                temp = string.Template(line)
                out_handle.write(temp.substitute(path=path))
    return target_file


def run_beye(directory, args):
    cmd = ['beye', '--output', directory] + args
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
            cdb = prepare_compilation_db(1, tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, ['--input', cdb])
            self.assertTrue(exit_code)
            self.assertTrue(os.path.isdir(outdir))

    def test_clear_deletes_report_dir(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_compilation_db(0, tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir, ['--input', cdb])
            self.assertFalse(exit_code)
            self.assertFalse(os.path.isdir(outdir))

    def test_clear_keeps_report_dir_when_asked(self):
        with fixtures.TempDir() as tmpdir:
            cdb = prepare_compilation_db(0, tmpdir)
            outdir = os.path.join(tmpdir, 'result')
            exit_code, output = run_beye(outdir,
                                         ['--input', cdb, '--keep-empty'])
            self.assertFalse(exit_code)
            self.assertTrue(os.path.isdir(outdir))
