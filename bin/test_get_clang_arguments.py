# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import analyzer as sut
import nose.tools
import tempfile
import os


def get_clang_arguments(opts):
    with tempfile.TemporaryDirectory() as tmpdir:
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
