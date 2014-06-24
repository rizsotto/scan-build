# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.core as sut
from nose.tools import assert_in, assert_equals
import fixtures
import os
import re


def assert_under_failures(path):
    assert_equals('failures', os.path.basename(os.path.dirname(path)))


def test_report_failure_create_files():
    with fixtures.TempDir() as tmpdir:
        # create input file
        with open(tmpdir + os.sep + 'test.c', 'w') as fd:
            fd.write('int main() { return 0; }')
        error_msg = 'this is my error output'
        uname_msg = 'this is my uname\n'
        # execute test
        opts = {'language': 'c',
                'directory': tmpdir,
                'file': 'test.c',
                'clang': 'clang',
                'uname': uname_msg,
                'html_dir': tmpdir,
                'error_type': 'other_error',
                'error_output': error_msg,
                'exit_code': 13}
        sut.report_failure(opts, lambda x: x)
        # verify the result
        result = dict()
        pp_file = None
        for root, _, files in os.walk(tmpdir):
            keys = [os.path.join(root, name) for name in files]
            for key in keys:
                with open(key, 'r') as fd:
                    result[key] = fd.readlines()
                if re.match('(.*/)+clang(.*)\.i', key):
                    pp_file = key

        # prepocessor file generated
        assert_under_failures(pp_file)
        # error file generated and content dumped
        error_file = pp_file + '.stderr.txt'
        assert_in(error_file, result)
        assert_under_failures(error_file)
        assert_equals([error_msg], result[error_file])
        # info file generated and content dumped
        info_file = pp_file + '.info.txt'
        assert_in(info_file, result)
        assert_under_failures(info_file)
        assert_equals('Other Error\n', result[info_file][1])
        assert_equals(uname_msg, result[info_file][3])
