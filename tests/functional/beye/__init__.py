# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from . import test_from_cdb
from . import test_from_cmd
from . import test_create_cdb
from . import test_exec_anatomy


def load_tests(loader, suite, pattern):
    suite.addTests(loader.loadTestsFromModule(test_from_cdb))
    suite.addTests(loader.loadTestsFromModule(test_from_cmd))
    suite.addTests(loader.loadTestsFromModule(test_create_cdb))
    suite.addTests(loader.loadTestsFromModule(test_exec_anatomy))
    return suite
