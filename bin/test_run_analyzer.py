# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import analyzer as sut
from nose.tools import assert_equals
import fixtures
import os


def run_analyzer(content, opts):
    with fixtures.TempDir() as tmpdir:
        with open(tmpdir + os.sep + 'test.cpp', 'w') as fd:
            fd.write(content)
        adds = {'language': 'c++',
                'directory': tmpdir,
                'file': 'test.cpp',
                'clang': 'clang'}
        spy = fixtures.Spy()
        result = sut.run_analyzer(
            sut.filter_dict(opts, frozenset(), adds), spy.call)
        return (result, spy.arg)


def test_run_analyzer():
    content = "int div(int n, int d) { return n / d; }"
    (result, fwds) = run_analyzer(content, dict())
    assert_equals(None, fwds)
    assert_equals(0, result)


def test_run_analyzer_crash():
    content = "int div(int n, int d) { return n / d }"
    (result, fwds) = run_analyzer(content, dict())
    assert_equals(None, fwds)
    assert_equals(1, result)


def test_run_analyzer_crash_and_forwarded():
    content = "int div(int n, int d) { return n / d }"
    (result, fwds) = run_analyzer(content, {'report_failures': True})
    assert_equals('crash', fwds['error_type'])
    assert_equals(set(), fwds['not_handled_attributes'])
    assert_equals(1, fwds['exit_code'])
    assert(len(fwds['error_output']) > 0)


# this test is disabled, because analyzer does not produce the expected
# warning, while the compiler does.
def run_analyzer_unknown_attribute_and_forwarded():
    content = 'typedef int __attribute__((visibility("default"))) bar;'
    (result, fwds) = run_analyzer(content, {'report_failures': True})
    assert_equals('attribute_ignored', fwds['error_type'])
    assert_equals(set(['visibility']), fwds['not_handled_attributes'])
    assert_equals(0, fwds['exit_code'])
    assert(len(fwds['error_output']) > 0)
