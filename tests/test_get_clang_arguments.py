# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.driver as sut
import tests.fixtures as fixtures
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


class GetClangArgumentsTest(fixtures.TestCase):

    def test_get_clang_arguments(self):
        opts = {'compile_options': ['-DNDEBUG', '-Dvar="this is it"']}
        result = get_clang_arguments(opts)
        self.assertIn('NDEBUG', result)
        self.assertIn('var="this is it"', result)

    def test_get_clang_arguments_fails(self):
        self.assertEquals(None,
                          sut.get_clang_arguments('.',
                                                  ['clang',
                                                   '-###',
                                                   '-fsyntax-only',
                                                   '-x',
                                                   'c',
                                                   'notexist.c']))
