# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
""" This module is responsible for to parse a compiler invocation. """

import re
import os

__all__ = ['Action', 'classify_parameters', 'is_source']


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
        elif arg in {'-E', '-S', '-cc1', '-M', '-MM'}:
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
        elif re.match(r'^[^-].+', arg) and is_source(arg):
            state['files'].append(arg)
        # and consider everything else as compile option.
        else:
            state['compile_options'].append(arg)

    return state


def is_source(filename):
    """ A predicate to decide the filename is a source file or not. """

    accepted = {
        '.c', '.cc', '.cp', '.cpp', '.cxx', '.c++', '.m', '.mm', '.i', '.ii',
        '.mii'
    }
    __, ext = os.path.splitext(filename)
    return ext.lower() in accepted


def cplusplus_compiler(name):
    """ Returns true when the compiler name refer to a C++ compiler. """

    match = re.match(r'^([^/]*/)*(\w*-)*(\w+\+\+)(-(\d+(\.\d+){0,3}))?$', name)
    return False if match is None else True
