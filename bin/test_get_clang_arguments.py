# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer as sut
import nose.tools
import fixtures
import os


def get_clang_arguments(opts):
    with fixtures.TempDir() as tmpdir:
        with open(tmpdir + os.sep + 'test.c', 'w') as fd:
            fd.write('')

        adds = {'language': 'c',
                'directory': tmpdir,
                'file': 'test.c',
                'clang': 'clang'}
        final = sut.filter_dict(opts, frozenset(), adds)
        args = sut.build_args(final, False)
        return sut.get_clang_arguments(tmpdir, args)


def test_get_clang_arguments():
    opts = {'compile_options': ['-DNDEBUG', '-Dvar="this is it"']}
    result = get_clang_arguments(opts)
    nose.tools.assert_in('NDEBUG', result)
    nose.tools.assert_in('var="this is it"', result)


def test_get_clang_arguments_fails():
    nose.tools.assert_equals(None,
                             sut.get_clang_arguments('.',
                                                     ['clang',
                                                      '-###',
                                                      '-fsyntax-only',
                                                      '-x',
                                                      'c',
                                                      'notexist.c']))
