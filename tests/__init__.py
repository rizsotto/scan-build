import unittest

import tests.unit
import tests.functional.beye


def suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(unit))
    suite.addTests(loader.loadTestsFromModule(functional.beye))
    return suite
