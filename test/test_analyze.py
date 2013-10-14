# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import beye.analyze as sut

def test_split_arguments():
    input = ['clang', '-Wall', '-std=C99', '-v', 'file.c']
    expected = ['clang', '-Wall', '-std', 'C99', '-v', 'file.c']
    assert expected == sut.split_arguments(input)


def test_action():
    def test(expected, cmds):
        assert expected == sut.Action.parse(cmds)

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
