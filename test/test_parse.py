# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import beye.analyze as sut
from nose.tools import assert_equals


def test_action():
    def test(expected, cmd):
        opts = sut.parse(cmd.split())
        assert_equals(expected, opts['action'])

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


def test_compile_opts():
    def test(cmd):
        opts = sut.parse(cmd.split())
        return opts.get('compile_options', [])

    assert_equals([], test('clang source.c'))
    assert_equals([], test('clang source.c -g -Wall'))
    assert_equals(['-nostdinc'], test('clang -c -nostdinc source.c'))
    assert_equals(['-fPIC'], test('clang -c source.c -fPIC'))


def test_optimalizations():
    def test(cmd):
        opts = sut.parse(cmd.split())
        return opts.get('compile_options', [])

    assert_equals(['-O1'], test('clang -c source.c -O'))
    assert_equals(['-O1'], test('clang -c source.c -O1'))
    assert_equals(['-O2'], test('clang -c source.c -Os'))
    assert_equals(['-O2'], test('clang -c source.c -O2'))
    assert_equals(['-O3'], test('clang -c source.c -O3'))


def test_input_file():
    cmd = 'clang -c -o source.o source.c -Wall -g'
    opts = sut.parse(cmd.split())
    assert_equals(opts['files'], ['source.c'])
    assert_equals(opts['output'], 'source.o')
    assert_equals(opts.get('language'), None)
    assert_equals(opts.get('archs_seen'), None)


def test_language():
    cmd = 'clang -c -o source.o source.c -x cpp'
    opts = sut.parse(cmd.split())
    assert_equals(opts['language'], 'cpp')


def test_arch():
    cmd = 'clang -c -o source.o source.c -arch i386 -arch mips'
    expected = ['-arch', 'i386', '-arch', 'mips']
    opts = sut.parse(cmd.split())
    assert_equals(opts.get('archs_seen'), expected)
    assert_equals(opts.get('compile_options'), expected)
    assert_equals(opts.get('link_options'), expected)


def test_include():
    cmd = 'clang -c -o source.o source.c -include /usr/local/include'
    opts = sut.parse(cmd.split())
    assert_equals(opts['compile_options'], ['-include', '/usr/local/include'])


def test_includes():
    cmd = 'clang -c -o source.o source.c -I/usr/local/include -I .'
    opts = sut.parse(cmd.split())
    assert_equals(opts['compile_options'], ['-I/usr/local/include', '-I', '.'])


def test_defines():
    cmd = 'clang -c -o source.o source.c -DNDEBUG -Dvariable=value'
    opts = sut.parse(cmd.split())
    assert_equals(opts['compile_options'], ['-DNDEBUG', '-Dvariable=value'])
