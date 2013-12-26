# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import beye.analyze as sut
from nose.tools import assert_equals


def test_language_from_filename():
    assert_equals('c', sut.language_from_filename('file.c'))
    assert_equals('c', sut.language_from_filename('./file.c'))
    assert_equals('c', sut.language_from_filename('./path/file.c'))
    assert_equals('c', sut.language_from_filename('./path.cpp/file.c'))
    assert_equals('c', sut.language_from_filename('/abs/path/file.c'))
    assert_equals('c++', sut.language_from_filename('./file.cpp'))
    assert_equals('c++', sut.language_from_filename('./file.cxx'))


def test_set_language():
    def test(expected, input):
        result = sut.set_language(input, lambda x: x)
        assert_equals(expected, result)

    l = 'language'
    f = 'file'
    test({f: 'file.c', l: 'c'}, {f: 'file.c', l: 'c'})
    test({f: 'file.c', l: 'c++'}, {f: 'file.c', l: 'c++'})
    test({f: 'file.c', l: 'c'}, {f: 'file.c'})
    test({f: 'file.cxx', l: 'c++'}, {f: 'file.cxx'})
    test(0, {f: 'file.i'})
    test(0, {f: 'file.i', l: 'c-cpp-output'})
    test(0, {f: 'file.java'})


def test_filter_dict_insert_works():
    input = {'key': 1}
    expected = {'key': 1, 'value': 2}
    assert_equals(expected, sut.filter_dict(input, [], {'value': 2}))


def test_filter_dict_delete_works():
    input = {'key': 1, 'value': 2}
    expected = {'value': 2}
    assert_equals(expected, sut.filter_dict(input, ['key', 'other'], dict()))


def test_filter_dict_modify_works():
    input = {'key': 1}
    expected = {'key': 2}
    assert_equals(expected, sut.filter_dict(input, ['key'], {'key': 2}))
    assert_equals(1, input['key'])


def test_arch_loop_default_forwards_call():
    input = {'key': 'value'}
    assert_equals(input, sut.arch_loop(input, lambda x: x))


def test_arch_loop_specified_forwards_call():
    input = {'archs_seen': ['-arch', 'i386', '-arch', 'ppc']}
    expected = {'arch': 'i386'}
    assert_equals(expected, sut.arch_loop(input, lambda x: x))


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


def test_arch_loop_stops_on_failure():
    spy = Spy('arch')
    input = {'archs_seen': ['-arch', spy.error_trigger, '-arch', 'i386']}
    assert_equals(spy.error_status, sut.arch_loop(input, spy.register))
    assert_equals([spy.error_trigger], spy.calls)


def test_files_loop_on_empty_forwards_call():
    input = {'key': 'value'}
    assert_equals(0, sut.files_loop(input, lambda x: x))


def test_files_loop_set_file_on_continuation():
    input = {'files': ['a']}
    assert_equals({'file': 'a'}, sut.files_loop(input, lambda x: x))


def test_files_loop_on_failure():
    spy = Spy('file')
    input = {'files': ['a', spy.error_trigger, 'b']}
    assert_equals(spy.error_status, sut.files_loop(input, spy.register))
    assert_equals(['a', spy.error_trigger], spy.calls)


def test_set_analyzer_output_on_not_specified_forwards_call():
    input = {'key': 'value'}
    assert_equals(input, sut.set_analyzer_output(input, lambda x: x))


def test_set_analyzer_output_create_temporary_file():
    spy = Spy('analyzer_output')
    input = {'output_format': 'plist'}
    status = sut.set_analyzer_output(input, spy.register)
    assert_equals(1, len(spy.calls))
