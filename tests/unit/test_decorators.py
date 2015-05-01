# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import libscanbuild.decorators as sut
import unittest


@sut.require([])
def method_without_expecteds(opts):
    return 0


@sut.require(['this', 'that'])
def method_with_expecteds(opts):
    return 0


@sut.require([])
def method_exception_from_inside(opts):
    raise Exception('here is one')


class RequireDecoratorTest(unittest.TestCase):

    def test_method_without_expecteds(self):
        self.assertEqual(method_without_expecteds(dict()), 0)
        self.assertEqual(method_without_expecteds({}), 0)
        self.assertEqual(method_without_expecteds({'this': 2}), 0)
        self.assertEqual(method_without_expecteds({'that': 3}), 0)

    def test_method_with_expecteds(self):
        self.assertRaises(KeyError, method_with_expecteds, dict())
        self.assertRaises(KeyError, method_with_expecteds, {})
        self.assertRaises(KeyError, method_with_expecteds, {'this': 2})
        self.assertRaises(KeyError, method_with_expecteds, {'that': 3})
        self.assertEqual(method_with_expecteds({'this': 0, 'that': 3}), 0)

    def test_method_exception_not_caught(self):
        self.assertRaises(Exception, method_exception_from_inside, dict())
