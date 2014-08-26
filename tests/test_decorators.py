# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.decorators as sut
import unittest
import tests.fixtures as fixtures


@sut.trace
def method_without_arguments():
    return 0


@sut.trace
def method_with_arguments(a, b):
    return 0


@sut.trace
def method_throws_exception():
    raise Exception('here we go')


class TraceDecoratorTest(unittest.TestCase):

    def setUp(self):
        self.traces = []
        sut.trace_method = lambda msg: self.traces.append(msg)

    def assertTraces(self, expected):
        self.assertEqual(self.traces, expected)

    def test_method_without_arguments(self):
        self.assertEqual(method_without_arguments(), 0)
        self.assertTraces(['entering method_without_arguments',
                           'leaving method_without_arguments'])

    def test_method_with_arguments(self):
        self.assertEqual(method_with_arguments(1, 2), 0)
        self.assertTraces(['entering method_with_arguments',
                           'leaving method_with_arguments'])

    def test_method_throws_exception(self):
        try:
            method_throws_exception()
            self.assertTrue(False, 'test is wrong')
        except:
            self.assertTraces(['entering method_throws_exception',
                               'exception in method_throws_exception',
                               'leaving method_throws_exception'])
