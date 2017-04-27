# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import libscanbuild as sut
import unittest


class ShellSplitTest(unittest.TestCase):

    def test_regular_commands(self):
        self.assertEqual([], sut.shell_split(""))
        self.assertEqual(['clang', '-c', 'file.c'],
                         sut.shell_split('clang -c file.c'))
        self.assertEqual(['clang', '-c', 'file.c'],
                         sut.shell_split('clang  -c  file.c'))
        self.assertEqual(['clang', '-c', 'file.c'],
                         sut.shell_split('clang -c\tfile.c'))

    def test_quoted_commands(self):
        self.assertEqual(['clang', '-c', 'file.c'],
                         sut.shell_split('"clang" -c "file.c"'))
        self.assertEqual(['clang', '-c', 'file.c'],
                         sut.shell_split("'clang' -c 'file.c'"))

    def test_shell_escaping(self):
        self.assertEqual(['clang', '-c', 'file.c', '-Dv=space value'],
                         sut.shell_split('clang -c file.c -Dv="space value"'))
        self.assertEqual(['clang', '-c', 'file.c', '-Dv=\"quote'],
                         sut.shell_split('clang -c file.c -Dv=\\\"quote'))
        self.assertEqual(['clang', '-c', 'file.c', '-Dv=(word)'],
                         sut.shell_split('clang -c file.c -Dv=\(word\)'))
