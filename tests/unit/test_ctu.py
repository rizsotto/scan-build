# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import unittest
import os.path
import libear
import libscanbuild.ctu as sut


class SymbolMapTest(unittest.TestCase):

    def assert_write_parse(self, content):
        with libear.temporary_directory() as tmp_dir:
            file_name = os.path.join(tmp_dir, 'test.syms')
            sut._write_symbol_map(file_name, iter(content))
            self.assertEqual(content,
                             list(sut._parse_symbol_map(file_name)))

    def test_serialize(self):
        entries = []
        self.assert_write_parse(entries)

        entries += [('_Z1fun1i@x86_64', 'ast/x86_64/fun1.c.ast')]
        self.assert_write_parse(entries)

        entries += [('_Z1fun2i@x86_64', 'ast/x86_64/fun2.c.ast')]
        self.assert_write_parse(entries)

        entries += [('_Z1fun3i@x86_64', 'ast/x86_64/fun3.c.ast')]
        self.assert_write_parse(entries)

        entries += [('_Z1fun3i@x86_64', 'ast/x86_64/fun with space.c.ast')]
        self.assert_write_parse(entries)

    def assert_does_not_filter(self, content):
        result = list(sut._filter_symbol_map(iter(content)))
        for elem in content:
            self.assertTrue(elem in result)
        for elem in result:
            self.assertTrue(elem in content)

    def test_filter_empty(self):
        self.assert_does_not_filter([])

    def test_filter_one(self):
        self.assert_does_not_filter(
            [('_Z1fun1i@x86_64', 'ast/x86_64/fun1.c.ast')])

    def test_filter_many(self):
        self.assert_does_not_filter(
            [('_Z1fun1i@x86_64', 'ast/x86_64/fun1.c.ast'),
             ('_Z1fun2i@x86_64', 'ast/x86_64/fun2.c.ast'),
             ('_Z1fun3i@x86_64', 'ast/x86_64/fun3.c.ast')])

    def test_filter_unique(self):
        input = [
            ('_Z1fun1i@x86_64', 'ast/x86_64/fun1.c.ast'),
            ('_Z1fun2i@x86_64', 'ast/x86_64/fun2.c.ast')
        ]
        # passing the same input twice
        result = list(sut._filter_symbol_map(iter(input + input)))
        # expect the the result be the input itself
        self.assertTrue(input[0] in result)
        self.assertTrue(input[1] in result)

    def test_filter_different(self):
        input = [
            ('_Z1fun1i@x86_64', 'ast/x86_64/fun1.c.ast'),
            ('_Z1fun2i@x86_64', 'ast/x86_64/fun2.c.ast'),
            ('_Z1fun1i@x86_64', 'ast/x86_64/fun3.c.ast')
        ]
        # only the second raw shall appear in the output.
        result = list(sut._filter_symbol_map(iter(input + input)))
        self.assertFalse(input[0] in result)
        self.assertTrue(input[1] in result)
        self.assertFalse(input[2] in result)
