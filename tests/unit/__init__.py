# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from . import test_parse
from . import test_analyze
from . import test_get_clang_arguments
from . import test_report_failure
from . import test_run_analyzer
from . import test_set_analyzer_output
from . import test_scan_file
from . import test_decorators
from . import test_get_prefix


def load_tests(loader, suite, pattern):
    suite.addTests(loader.loadTestsFromModule(test_parse))
    suite.addTests(loader.loadTestsFromModule(test_analyze))
    suite.addTests(loader.loadTestsFromModule(test_get_clang_arguments))
    suite.addTests(loader.loadTestsFromModule(test_report_failure))
    suite.addTests(loader.loadTestsFromModule(test_run_analyzer))
    suite.addTests(loader.loadTestsFromModule(test_set_analyzer_output))
    suite.addTests(loader.loadTestsFromModule(test_scan_file))
    suite.addTests(loader.loadTestsFromModule(test_decorators))
    suite.addTests(loader.loadTestsFromModule(test_get_prefix))
    return suite
