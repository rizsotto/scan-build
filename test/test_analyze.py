# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import beye.analyze as sut


def test_language_from_filename():
    assert 'c' == sut.language_from_filename('file.c')
    assert 'c' == sut.language_from_filename('./file.c')
    assert 'c' == sut.language_from_filename('./path/file.c')
    assert 'c' == sut.language_from_filename('./path.cpp/file.c')
    assert 'c' == sut.language_from_filename('/abs/path/file.c')
    assert 'c++' == sut.language_from_filename('./file.cpp')
    assert 'c++' == sut.language_from_filename('./file.cxx')


def test_is_accepted_language():
    assert True == sut.is_accepted_language('c')
    assert True == sut.is_accepted_language('c++')
    assert True == sut.is_accepted_language('objective-c')
    assert True == sut.is_accepted_language('objective-c++')
    assert False == sut.is_accepted_language('abap')
    assert False == sut.is_accepted_language(None)


def test_action():
    def test(expected, cmd):
        opts = sut.parse(cmd.split())
        assert expected == opts['action']

    Info = sut.Action.Info
    test(Info, 'clang source.c -print-prog-name')

    Link = sut.Action.Link
    test(Link, 'clang source.c')

    Compile = sut.Action.Compile
    test(Compile, 'clang -c source.c')
    test(Compile, 'clang -c source.c -MF source.d')

    Preprocess = sut.Action.Preprocess
    test(Preprocess, 'clang -E source.c')
    test(Preprocess, 'clang -c -E source.c')
    test(Preprocess, 'clang -c -M source.c')
    test(Preprocess, 'clang -c -MM source.c')


def test_archs_seen():
    def test(cmd):
        opts = sut.parse(cmd.split())
        return opts.get('archs_seen', set())

    assert set() == test('clang -c source.c')
    assert set(['ppc']) == test('clang -c -arch ppc source.c')
    assert set(['ppc', 'i386']) == test('clang -c -arch ppc -arch i386 source.c')


def test_compile_flags():
    def test(cmd):
        opts = sut.parse(cmd.split())
        return opts.get('compile_options', [])

    assert [] == test('clang source.c')
    assert ['-nostdinc', '-include', '/tmp'] == \
        test('clang -c -nostdinc source.c -include /tmp')


def test_complex_1():
    cmd = 'clang -c -Wall -g -o source.o source.c -std=C99 -fpic ' \
          '-arch i386 -O3 -x c'
    opts = sut.parse(cmd.split())
    assert opts['files'] == ['source.c']
    assert opts['output'] == 'source.o'
    assert opts['language'] == 'c'
    assert opts['action'] == sut.Action.Compile
    assert opts['archs_seen'] == set(['i386'])
    assert opts['compile_options'] == ['-std=C99', '-fpic', '-arch', 'i386', '-O3']


def test_complex_2():
    cmd = 'clang -c -o source.o source.c -I/usr/local/include'
    opts = sut.parse(cmd.split())
    assert opts['files'] == ['source.c']
    assert opts['output'] == 'source.o'
    assert opts.get('language') == None
    assert opts['action'] == sut.Action.Compile
    assert opts.get('archs_seen') == None
    assert opts['compile_options'] == ['-I/usr/local/include']


def test_new():
    cmd = 'clang -c -o source.o source.c -include /usr/local/include'
    opts = sut.parse(cmd.split())
    assert opts['action'] == sut.Action.Compile
    assert opts['compile_options'] == ['-include', '/usr/local/include']
