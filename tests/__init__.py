import unittest
import tests.unit.test_parse
import tests.unit.test_analyze
import tests.unit.test_get_clang_arguments
import tests.unit.test_report_failure
import tests.unit.test_run_analyzer
import tests.unit.test_set_analyzer_output
import tests.unit.test_scan_file
import tests.unit.test_decorators
import tests.unit.test_get_prefix


def suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(unit.test_parse))
    suite.addTests(loader.loadTestsFromModule(unit.test_analyze))
    suite.addTests(loader.loadTestsFromModule(unit.test_get_clang_arguments))
    suite.addTests(loader.loadTestsFromModule(unit.test_report_failure))
    suite.addTests(loader.loadTestsFromModule(unit.test_run_analyzer))
    suite.addTests(loader.loadTestsFromModule(unit.test_set_analyzer_output))
    suite.addTests(loader.loadTestsFromModule(unit.test_scan_file))
    suite.addTests(loader.loadTestsFromModule(unit.test_decorators))
    suite.addTests(loader.loadTestsFromModule(unit.test_get_prefix))
    return suite
