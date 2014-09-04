# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.runner as sut
import tests.unit.fixtures as fixtures
import os
import os.path
import re


class ReportFailureTest(fixtures.TestCase):

    def assertUnderFailures(self, path):
        self.assertEqual('failures', os.path.basename(os.path.dirname(path)))

    def test_report_failure_create_files(self):
        with fixtures.TempDir() as tmpdir:
            # create input file
            filename = os.path.join(tmpdir, 'test.c')
            with open(filename, 'w') as handle:
                handle.write('int main() { return 0')
            uname_msg = 'this is my uname\n'
            error_msg = 'this is my error output'
            # execute test
            opts = {'directory': os.getcwd(),
                    'file': filename,
                    'report': ['clang', '-fsyntax-only', '-E', filename],
                    'language': 'c',
                    'uname': uname_msg,
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
