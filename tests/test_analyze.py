# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.command as sut
import unittest
import tests.fixtures as fixtures


class AnalyzerTest(unittest.TestCase):

    def test_set_language(self):
        def test(expected, input):
            spy = fixtures.Spy()
            self.assertEqual(spy.success, sut.set_language(input, spy.call))
            self.assertEqual(expected, spy.arg)

        l = 'language'
        f = 'file'
        i = 'is_cxx'
        test({f: 'file.c', l: 'c'}, {f: 'file.c', l: 'c'})
        test({f: 'file.c', l: 'c++'}, {f: 'file.c', l: 'c++'})
        test({f: 'file.c', l: 'c++', i: True}, {f: 'file.c', i: True})
        test({f: 'file.c', l: 'c'}, {f: 'file.c'})
        test({f: 'file.cxx', l: 'c++'}, {f: 'file.cxx'})
        test({f: 'file.i', l: 'c-cpp-output'}, {f: 'file.i'})
        test({f: 'f.i', l: 'c-cpp-output'}, {f: 'f.i', l: 'c-cpp-output'})

    def test_set_language_fails(self):
        def test(expected, input):
            spy = fixtures.Spy()
            self.assertEqual(None, sut.set_language(input, spy.call))
            self.assertEqual(expected, spy.arg)

        test(None, {'file': 'file.java'})

    def test_arch_loop_default_forwards_call(self):
        spy = fixtures.Spy()
        input = {'key': 'value'}
        self.assertEqual(spy.success, sut.arch_loop(input, spy.call))
        self.assertEqual(input, spy.arg)

    def test_arch_loop_specified_forwards_call(self):
        spy = fixtures.Spy()
        input = {'archs_seen': ['-arch', 'i386', '-arch', 'ppc']}
        self.assertEqual(spy.success, sut.arch_loop(input, spy.call))
        self.assertEqual({'arch': 'i386'}, spy.arg)

    def test_arch_loop_forwards_call(self):
        spy = fixtures.Spy()
        input = {'archs_seen': ['-arch', 'i386', '-arch', 'sparc']}
        self.assertEqual(spy.success, sut.arch_loop(input, spy.call))
        self.assertEqual({'arch': 'sparc'}, spy.arg)
