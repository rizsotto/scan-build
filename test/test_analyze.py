# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.core as sut
from nose.tools import assert_equals, assert_not_equals
import fixtures


def test_set_language():
    def test(expected, input):
        spy = fixtures.Spy()
        assert_equals(spy.success, sut.set_language(input, spy.call))
        assert_equals(expected, spy.arg)

    l = 'language'
    f = 'file'
    i = 'is_cxx'
    test({f: 'file.c', l: 'c'}, {f: 'file.c', l: 'c'})
    test({f: 'file.c', l: 'c++'}, {f: 'file.c', l: 'c++'})
    test({f: 'file.c', l: 'c++', i: True}, {f: 'file.c', i: True})
    test({f: 'file.c', l: 'c'}, {f: 'file.c'})
    test({f: 'file.cxx', l: 'c++'}, {f: 'file.cxx'})
    test({f: 'file.i', l: 'c-cpp-output'}, {f: 'file.i'})
    test({f: 'file.i', l: 'c-cpp-output'}, {f: 'file.i', l: 'c-cpp-output'})
    test(None, {f: 'file.java'})


def test_filter_dict_insert_works():
    input = {'key': 1}
    expected = {'key': 1, 'value': 2}
    assert_equals(expected, sut.filter_dict(input, frozenset(), {'value': 2}))


def test_filter_dict_delete_works():
    input = {'key': 1, 'value': 2}
    expected = {'value': 2}
    assert_equals(
        expected, sut.filter_dict(input, frozenset(['key', 'other']), dict()))


def test_filter_dict_modify_works():
    input = {'key': 1}
    expected = {'key': 2}
    assert_equals(
        expected, sut.filter_dict(input, frozenset(['key']), {'key': 2}))
    assert_equals(1, input['key'])


def test_filter_dict_does_strip():
    input = {
        'good': 'has value',
        'bad': None,
        'another bad': None,
        'normal': 'also'}
    expected = {'good': 'has value', 'normal': 'also'}
    assert_equals(expected, sut.filter_dict(input, frozenset(), {}))


def test_arch_loop_default_forwards_call():
    spy = fixtures.Spy()
    input = {'key': 'value'}
    assert_equals(spy.success, sut.arch_loop(input, spy.call))
    assert_equals(input, spy.arg)


def test_arch_loop_specified_forwards_call():
    spy = fixtures.Spy()
    input = {'archs_seen': ['-arch', 'i386', '-arch', 'ppc']}
    assert_equals(spy.success, sut.arch_loop(input, spy.call))
    assert_equals({'arch': 'i386'}, spy.arg)


def test_arch_loop_stops_on_failure():
    spy = fixtures.Spy()
    input = {'archs_seen': ['-arch', 'sparc', '-arch', 'i386']}
    assert_not_equals(spy.success, sut.arch_loop(input, spy.fail))
    assert_equals({'arch': 'i386'}, spy.arg)


def test_files_loop_on_empty_forwards_call():
    spy = fixtures.Spy()
    input = {'key': 'value'}
    assert_equals(spy.success, sut.files_loop(input, spy.call))
    assert_equals(None, spy.arg)


def test_files_loop_set_file_on_continuation():
    spy = fixtures.Spy()
    input = {'files': ['a']}
    assert_equals(spy.success, sut.files_loop(input, spy.call))
    assert_equals({'file': 'a'}, spy.arg)


def test_files_loop_on_failure():
    spy = fixtures.Spy()
    input = {'files': ['a', 'b']}
    assert_not_equals(spy.success, sut.files_loop(input, spy.fail))
    assert_equals({'file': 'b'}, spy.arg)
