# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import analyzer as sut
from nose.tools import assert_equals


def test_action():
    def test(expected, cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(expected, opts['action'])

    Info = sut.Action.Info
    test(Info, ['clang', 'source.c', '-print-prog-name'])

    Link = sut.Action.Link
    test(Link, ['clang', 'source.c'])

    Compile = sut.Action.Compile
    test(Compile, ['clang', '-c', 'source.c'])
    test(Compile, ['clang', '-c', 'source.c', '-MF', 'source.d'])

    Preprocess = sut.Action.Preprocess
    test(Preprocess, ['clang', '-E', 'source.c'])
    test(Preprocess, ['clang', '-c', '-E', 'source.c'])
    test(Preprocess, ['clang', '-c', '-M', 'source.c'])
    test(Preprocess, ['clang', '-c', '-MM', 'source.c'])


def test_optimalizations():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        return opts.get('compile_options', [])

    assert_equals(['-O1'], test(['clang', '-c', 'source.c', '-O']))
    assert_equals(['-O1'], test(['clang', '-c', 'source.c', '-O1']))
    assert_equals(['-O2'], test(['clang', '-c', 'source.c', '-Os']))
    assert_equals(['-O2'], test(['clang', '-c', 'source.c', '-O2']))
    assert_equals(['-O3'], test(['clang', '-c', 'source.c', '-O3']))


def test_language():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        return opts.get('language')

    assert_equals(None, test(['clang', '-c', 'source.c']))
    assert_equals('c', test(['clang', '-c', 'source.c', '-x', 'c']))
    assert_equals('cpp', test(['clang', '-c', 'source.c', '-x', 'cpp']))


def test_arch():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(opts.get('archs_seen'), opts.get('compile_options'))
        assert_equals(opts.get('archs_seen'), opts.get('link_options'))
        return opts.get('archs_seen', [])

    eq = assert_equals

    eq([], test(['clang', '-c', 'source.c']))
    eq(['-arch', 'mips'],
       test(['clang', '-c', 'source.c', '-arch', 'mips']))
    eq(['-arch', 'mips', '-arch', 'i386'],
       test(['clang', '-c', 'source.c', '-arch', 'mips', '-arch', 'i386']))


def test_input_file():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        return opts.get('files', [])

    assert_equals(['src.c'], test(['clang', 'src.c']))
    assert_equals(['src.c'], test(['clang', '-c', 'src.c']))
    assert_equals(['s1.c', 's2.c'], test(['clang', '-c', 's1.c', 's2.c']))


def test_output_file():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        return opts.get('output', None)

    assert_equals(None, test(['clang', 'src.c']))
    assert_equals('src.o', test(['clang', '-c', 'src.c', '-o', 'src.o']))
    assert_equals('src.o', test(['clang', '-c', '-o', 'src.o', 'src.c']))


def test_include():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(None, opts.get('link_options'))
        return opts.get('compile_options', [])

    eq = assert_equals

    eq([], test(['clang', '-c', 'src.c']))
    eq(['-include', '/usr/local/include'],
       test(['clang', '-c', 'src.c', '-include', '/usr/local/include']))
    eq(['-I.'],
       test(['clang', '-c', 'src.c', '-I.']))
    eq(['-I', '.'],
       test(['clang', '-c', 'src.c', '-I', '.']))
    eq(['-I/usr/local/include'],
       test(['clang', '-c', 'src.c', '-I/usr/local/include']))
    eq(['-I', '/usr/local/include'],
       test(['clang', '-c', 'src.c', '-I', '/usr/local/include']))
    eq(['-I/opt', '-I', '/usr/local/include'],
       test(['clang', '-c', 'src.c', '-I/opt', '-I', '/usr/local/include']))


def test_define():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(None, opts.get('link_options'))
        return opts.get('compile_options', [])

    eq = assert_equals

    eq([], test(['clang', '-c', 'src.c']))
    eq(['-DNDEBUG'],
       test(['clang', '-c', 'src.c', '-DNDEBUG']))
    eq(['-UNDEBUG'],
       test(['clang', '-c', 'src.c', '-UNDEBUG']))
    eq(['-Dvar1=val1', '-Dvar2=val2'],
       test(['clang', '-c', 'src.c', '-Dvar1=val1', '-Dvar2=val2']))
    eq(['-Dvar="val ues"'],
       test(['clang', '-c', 'src.c', '-Dvar="val ues"']))


def test_link_only_flags():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(None, opts.get('compile_options'))
        return opts.get('link_options', [])

    eq = assert_equals

    eq([],
       test(['clang', 'src.o']))
    eq(['-lrt', '-L/opt/company/lib'],
       test(['clang', 'src.o', '-lrt', '-L/opt/company/lib']))
    eq(['-framework', 'foo'],
       test(['clang', 'src.o', '-framework', 'foo']))


def test_compile_only_flags():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(None, opts.get('link_options'))
        return opts.get('compile_options', [])

    eq = assert_equals

    eq([], test(['clang', '-c', 'src.c']))
    eq([],
       test(['clang', '-c', 'src.c', '-Wnoexcept']))
    eq([],
       test(['clang', '-c', 'src.c', '-Wall']))
    eq(['-Wno-cpp'],
       test(['clang', '-c', 'src.c', '-Wno-cpp']))
    eq(['-std=C99'],
       test(['clang', '-c', 'src.c', '-std=C99']))
    eq(['-mtune=i386', '-mcpu=i386'],
       test(['clang', '-c', 'src.c', '-mtune=i386', '-mcpu=i386']))
    eq(['-nostdinc'],
       test(['clang', '-c', 'src.c', '-nostdinc']))
    eq(['-isystem', '/image/debian'],
       test(['clang', '-c', 'src.c', '-isystem', '/image/debian']))
    eq(['-iprefix', '/usr/local'],
       test(['clang', '-c', 'src.c', '-iprefix', '/usr/local']))
    eq(['-iquote=me'],
       test(['clang', '-c', 'src.c', '-iquote=me']))
    eq(['-iquote', 'me'],
       test(['clang', '-c', 'src.c', '-iquote', 'me']))


def test_compile_and_link_flags():
    def test(cmd):
        opts = sut.parse({'command': cmd}, lambda x: x)
        assert_equals(opts.get('compile_options'), opts.get('link_options'))
        return opts.get('compile_options', [])

    eq = assert_equals

    eq([],
       test(['clang', '-c', 'src.c', '-fsyntax-only']))
    eq(['-fsinged-char'],
       test(['clang', '-c', 'src.c', '-fsinged-char']))
    eq(['-fPIC'],
       test(['clang', '-c', 'src.c', '-fPIC']))
    eq(['-stdlib=libc++'],
       test(['clang', '-c', 'src.c', '-stdlib=libc++']))
    eq(['--sysroot', '/'],
       test(['clang', '-c', 'src.c', '--sysroot', '/']))
    eq(['-isysroot', '/'],
       test(['clang', '-c', 'src.c', '-isysroot', '/']))
    eq([],
       test(['clang', '-c', 'src.c', '-sectorder', 'a', 'b', 'c']))
