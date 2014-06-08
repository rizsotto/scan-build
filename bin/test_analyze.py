# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import analyzer as sut
from nose.tools import assert_equals


def test_set_language():
    def test(expected, input):
        result = sut.set_language(input, lambda x: x)
        assert_equals(expected, result)

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
    test(0, {f: 'file.java'})


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


class Spy:

    def __init__(self, attribute_name):
        self.attribute = attribute_name
        self.calls = []
        self.error_status = 500
        self.error_trigger = 'broken'

    def register(self, arg):
        self.calls.append(arg[self.attribute])
        if arg[self.attribute] == self.error_trigger:
            return self.error_status
        else:
            return 0


def test_arch_loop_default_forwards_call():
    spy = Spy('key')
    input = {'key': 'value'}
    assert_equals(0, sut.arch_loop(input, spy.register))
    assert_equals(['value'], spy.calls)


def test_arch_loop_specified_forwards_call():
    spy = Spy('arch')
    input = {'archs_seen': ['-arch', 'i386', '-arch', 'ppc']}
    assert_equals(0, sut.arch_loop(input, spy.register))
    assert_equals(['i386'], spy.calls)


def test_arch_loop_stops_on_failure():
    spy = Spy('arch')
    input = {'archs_seen': ['-arch', spy.error_trigger, '-arch', 'i386']}
    assert_equals(spy.error_status, sut.arch_loop(input, spy.register))
    assert_equals([spy.error_trigger, 'i386'], spy.calls)


def test_files_loop_on_empty_forwards_call():
    spy = Spy('file')
    input = {'key': 'value'}
    assert_equals(0, sut.files_loop(input, spy.register))
    assert_equals([], spy.calls)


def test_files_loop_set_file_on_continuation():
    spy = Spy('file')
    input = {'files': ['a']}
    assert_equals(0, sut.files_loop(input, spy.register))
    assert_equals(['a'], spy.calls)


def test_files_loop_on_failure():
    spy = Spy('file')
    input = {'files': ['a', spy.error_trigger, 'b']}
    assert_equals(spy.error_status, sut.files_loop(input, spy.register))
    assert_equals(['a', spy.error_trigger, 'b'], spy.calls)
