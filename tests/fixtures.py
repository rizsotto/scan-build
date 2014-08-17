# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import tempfile
import shutil
import unittest


class Spy:

    def __init__(self):
        self.arg = None
        self.success = 0

    def call(self, params):
        self.arg = params
        return self.success


class TempDir:

    def __init__(self):
        self.name = tempfile.mkdtemp('.test', 'beye', None)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.name is not None:
            shutil.rmtree(self.name)


class TestCase(unittest.TestCase):

    def assertIn(self, element, collection):
        found = False
        for it in collection:
            if element == it:
                found = True

        self.assertTrue(found, '{0} does not have {1}'.format(collection,
                                                              element))
