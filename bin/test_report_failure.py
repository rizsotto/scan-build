# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import analyzer as sut
from nose.tools import assert_in, assert_equals
import fixtures
import os


def assert_under_failures(arg):
    (path, _) = arg
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
                'not_handled_attributes': ['dllimport', 'dllexport'],
                'exit_code': 13}
        sut.report_failure(opts, lambda x: x)
        # verify the result
        result = dict()
        for root, _, files in os.walk(tmpdir):
            keys = [os.path.join(root, name) for name in files]
            for key in keys:
                with open(key, 'r') as fd:
                    result[os.path.basename(key)] = (key, fd.readlines())

        # ignored attribute files generated
        assert_in('attribute_ignored_dllexport.txt', result)
        assert_under_failures(result['attribute_ignored_dllexport.txt'])
        assert_in('attribute_ignored_dllimport.txt', result)
        assert_under_failures(result['attribute_ignored_dllimport.txt'])
        # prepocessor file generated
        (_, [pp_file]) = result['attribute_ignored_dllimport.txt']
        assert_in(pp_file, result)
        assert_under_failures(result[pp_file])
        # error file generated and content dumped
        error_file = pp_file + '.stderr.txt'
        assert_in(error_file, result)
        assert_under_failures(result[error_file])
        assert_equals([error_msg], result[error_file][1])
        # info file generated and content dumped
        info_file = pp_file + '.info.txt'
        assert_in(info_file, result)
        assert_under_failures(result[info_file])
        assert_equals('Other Error\n', result[info_file][1][1])
        assert_equals(uname_msg, result[info_file][1][3])
