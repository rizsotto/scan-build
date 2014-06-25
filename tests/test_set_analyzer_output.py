# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.core as sut
import tests.fixtures as fixtures
import unittest
import os


class SetAnalyzerOutputTest(fixtures.TestCase):

    def test_set_analyzer_output_forwarded(self):
        spy = fixtures.Spy()
        sut.set_analyzer_output(dict(), spy.call)
        self.assertEquals(dict(), spy.arg)

    def test_set_analyzer_output_create_file(self):
        class Spy:
            def __init__(self):
                self.arg = None

            def call(self, params):
                self.arg = params
                with open(params['analyzer_output'], 'w') as fd:
                    fd.write('hello from here')

        with fixtures.TempDir() as tmpdir:
            opts = {'html_dir': tmpdir, 'output_format': 'plist'}
            spy = Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['analyzer_output']))

    def test_set_analyzer_output_delete_empty_file(self):
        class Spy:
            def __init__(self):
                self.arg = None

            def call(self, params):
                self.arg = params

        with fixtures.TempDir() as tmpdir:
            opts = {'html_dir': tmpdir, 'output_format': 'plist'}
            spy = Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertFalse(os.path.exists(spy.arg['analyzer_output']))
