# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import beye.analyze as sut


def test_split_arguments():
    input = ['clang', '-Wall', '-std=C99', '-v', 'file.c']
    expected = ['clang', '-Wall', '-std', 'C99', '-v', 'file.c']
    assert expected == sut.Parser.split_arguments(input)


def test_action():
    def test(expected, cmds):
        parser = sut.Parser.run(cmds)
        assert expected == parser.get_action()

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


def test_archs_seen():
    def test(cmds):
        parser = sut.Parser.run(cmds)
        return parser.archs_seen

    assert [] == test(['clang', '-c', 'source.c'])
    assert ['ppc'] == test(['clang', '-c', '-arch', 'ppc', 'source.c'])
    assert ['ppc', 'i386'] == test(['clang', '-c', '-arch', 'ppc',
                                    '-arch', 'i386', 'source.c'])
