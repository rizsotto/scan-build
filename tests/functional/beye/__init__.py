# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from . import test_from_cdb
from . import test_create_cdb


def load_tests(loader, suite, pattern):
    suite.addTests(loader.loadTestsFromModule(test_from_cdb))
    suite.addTests(loader.loadTestsFromModule(test_create_cdb))
    return suite
