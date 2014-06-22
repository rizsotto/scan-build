# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from bin import analyzer as sut
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
    assert_equals(1, fwds['exit_code'])
    assert(len(fwds['error_output']) > 0)
