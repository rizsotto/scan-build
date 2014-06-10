# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import tempfile
import shutil


class Spy:
    def __init__(self):
        self.arg = None
        self.success = 0
        self.error = 500

    def call(self, params):
        self.arg = params
        return self.success

    def fail(self, params):
        self.arg = params
        return self.error


class TempDir:

    def __init__(self):
        self.name = tempfile.mkdtemp('.test', 'beye', None)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def cleanup(self):
        if self.name is not None:
            shutil.rmtree(self.name)
