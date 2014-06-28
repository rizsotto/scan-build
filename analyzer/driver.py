# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

from analyzer.core import *
import re
import itertools


def run():
    pass


def get_default_checkers(clang):
    """ To get the default plugins we execute Clang to print how this
    comilation would be called. For input file we specify stdin. And
    pass only language information. """
    def checkers(language):
        pattern = re.compile('^-analyzer-checker=(.*)$')
        cmd = [clang, '--analyze', '-x', language, '-']
        return [pattern.match(arg).group(1)
                for arg
                in get_clang_arguments('.', cmd)
                if pattern.match(arg)]

    return set(itertools.chain.from_iterable(
               [checkers(language)
                for language
                in ['c', 'c++', 'objective-c', 'objective-c++']]))
