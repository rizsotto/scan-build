import unittest
import tests.test_parse
import tests.test_analyze
import tests.test_get_clang_arguments
import tests.test_report_failure
import tests.test_run_analyzer
import tests.test_set_analyzer_output


def suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(test_parse))
    suite.addTests(loader.loadTestsFromModule(test_analyze))
    suite.addTests(loader.loadTestsFromModule(test_get_clang_arguments))
    suite.addTests(loader.loadTestsFromModule(test_report_failure))
    suite.addTests(loader.loadTestsFromModule(test_run_analyzer))
    suite.addTests(loader.loadTestsFromModule(test_set_analyzer_output))
    return suite
