# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.beye as sut
from . import fixtures


class GetPrefixFromCompilationDatabaseTest(fixtures.TestCase):

    def test_with_different_filenames(self):
        self.assertEqual(
            sut._commonprefix(['/tmp/a.c', '/tmp/b.c']), '/tmp')

    def test_with_different_dirnames(self):
        self.assertEqual(
            sut._commonprefix(['/tmp/abs/a.c', '/tmp/ack/b.c']), '/tmp')

    def test_no_common_prefix(self):
        self.assertEqual(
            sut._commonprefix(['/tmp/abs/a.c', '/usr/ack/b.c']), '/')

    def test_with_single_file(self):
        self.assertEqual(
            sut._commonprefix(['/tmp/a.c']), '/tmp')

    def test_empty(self):
        self.assertEqual(
            sut._commonprefix([]), '')

    def test_not_existing_compilation_database(self):
        self.assertRaises(Exception, sut.get_prefix_from, '/notexist.json')
