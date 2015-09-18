# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
""" This module is responsible for to parse a compiler invocation. """

import re
import os

__all__ = ['Action', 'classify_parameters', 'classify_source']


class Action(object):
    """ Enumeration class for compiler action. """

    Link, Compile, Ignored = range(3)


def classify_parameters(command):
    """ Parses the command line arguments of the given invocation. """

    def action(values, value):
        current = values.get('action', value)
        values.update({'action': max(current, value)})

    state = {
        'action': Action.Link,
        'files': [],
        'compile_options': [],
        'c++': cplusplus_compiler(command[0])
    }

    args = iter(command[1:])
    for arg in args:
        # compiler action parameters are the most important ones...
        if arg == '-c':
            action(state, Action.Compile)
        elif arg in {'-E', '-S', '-cc1', '-M', '-MM', '-###'}:
            action(state, Action.Ignored)
        # take arch flags
        elif arg == '-arch':
            archs = state.get('archs_seen', [])
            state.update({'archs_seen': archs + [next(args)]})
        # explicit language option saved
        elif arg == '-x':
            state.update({'language': next(args)})
        # some preprocessor parameters are ignored...
        elif arg in {'-MD', '-MMD', '-MG', '-MP'}:
            pass
        elif arg in {'-MF', '-MT', '-MQ'}:
            next(args)
        # linker options are ignored...
        elif arg in {'-static', '-shared', '-s', '-rdynamic'}:
            pass
        elif re.match(r'^-[lL].+', arg):
            pass
        elif arg in {'-l', '-L', '-u', '-z', '-T', '-Xlinker'}:
            next(args)
        # optimalization and waring options are ignored...
        elif re.match(r'^-([mW].+|O.*)', arg):
            pass
        # parameters which looks source file are taken...
        elif re.match(r'^[^-].+', arg) and classify_source(arg):
            state['files'].append(arg)
        # and consider everything else as compile option.
        else:
            state['compile_options'].append(arg)

    return state


def classify_source(filename, cplusplus=False):
    """ Return the language from fille name extension. """

    mapping = {
        '.c': 'c++' if cplusplus else 'c',
        '.i': 'c++-cpp-output' if cplusplus else 'c-cpp-output',
        '.ii': 'c++-cpp-output',
        '.m': 'objective-c',
        '.mi': 'objective-c-cpp-output',
        '.mm': 'objective-c++',
        '.mii': 'objective-c++-cpp-output',
        '.C': 'c++',
        '.cc': 'c++',
        '.CC': 'c++',
        '.cp': 'c++',
        '.cpp': 'c++',
        '.cxx': 'c++',
        '.c++': 'c++',
        '.C++': 'c++',
        '.txx': 'c++'
    }

    __, extension = os.path.splitext(os.path.basename(filename))
    return mapping.get(extension)


def cplusplus_compiler(name):
    """ Returns true when the compiler name refer to a C++ compiler. """

    match = re.match(r'^([^/]*/)*(\w*-)*(\w+\+\+)(-(\d+(\.\d+){0,3}))?$', name)
    return False if match is None else True
