from . import test_from_cdb


def load_tests(loader, suite, pattern):
    suite.addTests(loader.loadTestsFromModule(test_from_cdb))
    return suite
