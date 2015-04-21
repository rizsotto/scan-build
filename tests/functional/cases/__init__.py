# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import os.path
import subprocess


def load_tests(loader, suite, pattern):
    from . import test_from_cdb
    suite.addTests(loader.loadTestsFromModule(test_from_cdb))
    from . import test_from_cmd
    suite.addTests(loader.loadTestsFromModule(test_from_cmd))
    from . import test_create_cdb
    suite.addTests(loader.loadTestsFromModule(test_create_cdb))
    from . import test_exec_anatomy
    suite.addTests(loader.loadTestsFromModule(test_exec_anatomy))
    return suite


def make_args(target):
    this_dir, _ = os.path.split(__file__)
    path = os.path.normpath(os.path.join(this_dir, '..', 'src'))
    return ['make',
            'SRCDIR={}'.format(path),
            'OBJDIR={}'.format(target),
            '-f', os.path.join(path, 'build', 'Makefile')]


def silent_call(cmd):
    return subprocess.call(cmd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)


def silent_check_call(cmd):
    return subprocess.check_call(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
