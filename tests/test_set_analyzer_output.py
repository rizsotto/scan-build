# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.runner as sut
import tests.fixtures as fixtures
import os


class SetAnalyzerOutputTest(fixtures.TestCase):

    def test_html(self):
        with fixtures.TempDir() as tmpdir:
            opts = {'out_dir': tmpdir, 'output_format': 'html'}
            spy = fixtures.Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['output'][1]))
            self.assertTrue(os.path.isdir(spy.arg['output'][1]))

    def test_plist_html(self):
        with fixtures.TempDir() as tmpdir:
            opts = {'out_dir': tmpdir, 'output_format': 'plist-html'}
            spy = fixtures.Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['output'][1]))
            self.assertTrue(os.path.isfile(spy.arg['output'][1]))

    def test_plist(self):
        with fixtures.TempDir() as tmpdir:
            opts = {'out_dir': tmpdir, 'output_format': 'plist'}
            spy = fixtures.Spy()
            sut.set_analyzer_output(opts, spy.call)
            self.assertTrue(os.path.exists(spy.arg['output'][1]))
            self.assertTrue(os.path.isfile(spy.arg['output'][1]))
