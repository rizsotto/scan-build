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
        class Spy:
            def __init__(self):
                self.result = None
            def catch(self, out):
                self.result = out

        spy = Spy()
        sut.set_language(input, spy.catch)
        assert_equals(expected, spy.result)

    l = 'language'
    f = 'file'
    test({f: 'file.c', l: 'c'}, {f: 'file.c', l: 'c'})
    test({f: 'file.c', l: 'c++'}, {f: 'file.c', l: 'c++'})
    test({f: 'file.c', l: 'c'}, {f: 'file.c'})
    test({f: 'file.cxx', l: 'c++'}, {f: 'file.cxx'})
    test(None, {f: 'file.i'})
    test(None, {f: 'file.i', l: 'c-cpp-output'})
    test(None, {f: 'file.java'})
