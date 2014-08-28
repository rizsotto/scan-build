# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.beye as sut
import tests.fixtures as fixtures
import os.path
import json


def get_prefix(filenames):
    with fixtures.TempDir() as tmpdir:
        database = os.path.join(tmpdir, 'input.json')
        with open(database, 'w') as handle:
            content = [{'file': entry} for entry in filenames]
            json.dump(content, handle)

        return sut.get_prefix_from(database)


class GetPrefixFromCompilationDatabaseTest(fixtures.TestCase):

    def test_with_different_filenames(self):
        self.assertEqual(get_prefix(['/tmp/a.c', '/tmp/b.c']), '/tmp')

    def test_with_different_dirnames(self):
        self.assertEqual(get_prefix(['/tmp/abs/a.c', '/tmp/ack/b.c']), '/tmp')

    def test_no_common_prefix(self):
        self.assertEqual(get_prefix(['/tmp/abs/a.c', '/usr/ack/b.c']), '/')

    def test_with_single_file(self):
        self.assertEqual(get_prefix(['/tmp/a.c']), '/tmp')

    def test_empty(self):
        self.assertEqual(get_prefix([]), '')

    def test_not_existing_compilation_database(self):
        self.assertRaises(Exception, sut.get_prefix_from, '/notexist.json')
