# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import unittest

import tests.unit
import tests.functional.cases


def suite():
    loader = unittest.TestLoader()
    ts = unittest.TestSuite()
    ts.addTests(loader.loadTestsFromModule(tests.unit))
    ts.addTests(loader.loadTestsFromModule(tests.functional.cases))
    return ts
