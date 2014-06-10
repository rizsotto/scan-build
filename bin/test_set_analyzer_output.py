# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import analyzer as sut
from nose.tools import assert_equals, assert_in, assert_true, assert_false
import fixtures
import os


def test_set_analyzer_output_forwarded():
    spy = fixtures.Spy()
    sut.set_analyzer_output(dict(), spy.call)
    assert_equals(dict(), spy.arg)


def test_set_analyzer_output_create_file():
    class Spy:
        def __init__(self):
            self.arg = None

        def call(self, params):
            self.arg = params

            assert_in('analyzer_output', params)
            with open(params['analyzer_output'], 'w') as fd:
                fd.write('hello from here')
                fd.close()

    with fixtures.TempDir() as tmpdir:
        opts = {'html_dir': tmpdir, 'output_format': 'plist'}
        spy = Spy()
        sut.set_analyzer_output(opts, spy.call)
        assert_true(os.path.exists(spy.arg['analyzer_output']))


def test_set_analyzer_output_delete_empty_file():
    class Spy:
        def __init__(self):
            self.arg = None

        def call(self, params):
            self.arg = params
            assert_in('analyzer_output', params)

    with fixtures.TempDir() as tmpdir:
        opts = {'html_dir': tmpdir, 'output_format': 'plist'}
        spy = Spy()
        sut.set_analyzer_output(opts, spy.call)
        assert_false(os.path.exists(spy.arg['analyzer_output']))
