# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
""" This module is responsible for to parse a compiler invocation. """

import re

__all__ = ['Action', 'classify_parameters']


class Action(object):
    """ Enumeration class for compiler action. """

    Link, Compile, Preprocess, Info, Internal = range(5)


def classify_parameters(command):
    """ Parses the command line arguments of the given invocation.

    To run analysis from a compilation command, first it disassembles the
    compilation command. Classifies the parameters into groups and throws
    away those which are not relevant. """

    def match(state, iterator):
        """ This method contains a list of pattern and action tuples.
        The matching start from the top if the list, when the first match
        happens the action is executed. """

        def regex(pattern, action):
            """ Matching expression for regex. """

            def evaluate(iterator):
                match = evaluate.regexp.match(iterator.current())
                if match:
                    action(state, iterator, match)
                    return True

            evaluate.regexp = re.compile(pattern)
            return evaluate

        def anyof(opts, action):
            """ Matching expression for string literals. """

            def evaluate(iterator):
                if iterator.current() in opts:
                    action(state, iterator, None)
                    return True

            return evaluate

        tasks = [
            # actions
            regex(r'^-(E|MM?)$', take_action(Action.Preprocess)),
            anyof({'-c'}, take_action(Action.Compile)),
            anyof({'-print-prog-name'}, take_action(Action.Info)),
            anyof({'-cc1'}, take_action(Action.Internal)),
            # architectures
            anyof({'-arch'}, take_two('archs_seen')),
            # module names
            anyof({'-filelist'}, take_from_file('files')),
            regex(r'^[^-].+', take_one('files')),
            # language
            anyof({'-x'}, take_second('language')),
            # output
            anyof({'-o'}, take_second('output')),
            # relevant compiler flags
            anyof({'-write-strings', '-v'}, take_one('compile_options')),
            anyof({'-ftrapv-handler', '--sysroot', '-target'},
                  take_two('compile_options')),
            regex(r'^-isysroot', take_two('compile_options')),
            regex(r'^-m(32|64)$', take_one('compile_options')),
            regex(r'^-mios-simulator-version-min(.*)',
                  take_joined('compile_options')),
            regex(r'^-stdlib(.*)', take_joined('compile_options')),
            regex(r'^-mmacosx-version-min(.*)',
                  take_joined('compile_options')),
            regex(r'^-miphoneos-version-min(.*)',
                  take_joined('compile_options')),
            regex(r'^-O[1-3]$', take_one('compile_options')),
            anyof({'-O'}, take_as('-O1', 'compile_options')),
            anyof({'-Os'}, take_as('-O2', 'compile_options')),
            regex(r'^-[DIU](.*)$', take_joined('compile_options')),
            regex(r'^-isystem(.*)$', take_joined('compile_options')),
            anyof({'-nostdinc'}, take_one('compile_options')),
            regex(r'^-std=', take_one('compile_options')),
            regex(r'^-include', take_two('compile_options')),
            anyof({
                '-idirafter', '-imacros', '-iprefix', '-iwithprefix',
                '-iwithprefixbefore'
            }, take_two('compile_options')),
            regex(r'^-m.*', take_one('compile_options')),
            regex(r'^-iquote(.*)', take_joined('compile_options')),
            regex(r'^-Wno-', take_one('compile_options')),
            # ignored flags
            regex(r'^-framework$', take_two()),
            regex(r'^-fobjc-link-runtime(.*)', take_joined()),
            regex(r'^-[lL]', take_one()),
            regex(r'^-M[TF]$', take_two()),
            regex(r'^-[eu]$', take_two()),
            anyof({'-fsyntax-only', '-save-temps'}, take_one()),
            anyof({
                '-install_name', '-exported_symbols_list', '-current_version',
                '-compatibility_version', '-init', '-seg1addr',
                '-bundle_loader', '-multiply_defined', '--param',
                '--serialize-diagnostics'
            }, take_two()),
            anyof({'-sectorder'}, take_four()),
            # relevant compiler flags
            regex(r'^-[fF](.+)$', take_one('compile_options'))
        ]
        for task in tasks:
            if task(iterator):
                return

    state = {'action': Action.Link, 'cxx': is_cplusplus_compiler(command[0])}

    arguments = Arguments(command)
    for _ in arguments:
        match(state, arguments)
    return state


class Arguments(object):
    """ An iterator wraper around compiler arguments.

    Python iterators are only implement the 'next' method, but this one
    implements the 'current' query method as well. """

    def __init__(self, args):
        """ Takes full command line, but iterates on the parameters only. """

        self.__sequence = [arg for arg in args[1:] if arg != '']
        self.__size = len(self.__sequence)
        self.__current = -1

    def __iter__(self):
        """ Needed for python iterator. """

        return self

    def __next__(self):
        """ Needed for python iterator. (version 3.x) """

        return self.next()

    def next(self):
        """ Needed for python iterator. (version 2.x) """

        self.__current += 1
        return self.current()

    def current(self):
        """ Extra method to query the current element. """

        if self.__current >= self.__size:
            raise StopIteration
        else:
            return self.__sequence[self.__current]


def take_n(count=1, *keys):
    """ Take N number of arguments and append it to the refered values. """

    def take(values, iterator, _match):
        updates = []
        updates.append(iterator.current())
        for _ in range(count - 1):
            updates.append(iterator.next())
        for key in keys:
            current = values.get(key, [])
            values.update({key: current + updates})

    return take


def take_one(*keys):
    """ Take one argument and append to the 'key' values. """

    return take_n(1, *keys)


def take_two(*keys):
    """ Take two arguments and append to the 'key' values. """

    return take_n(2, *keys)


def take_four(*keys):
    """ Take four arguments and append to the 'key' values. """

    return take_n(4, *keys)


def take_joined(*keys):
    """ Take one or two arguments and append to the 'key' values.

    eg.: '-Isomething' shall take only one.
         '-I something' shall take two.

    This action should go with regex matcher only. """

    def take(values, iterator, match):
        updates = []
        updates.append(iterator.current())
        if not match.group(1):
            updates.append(iterator.next())
        for key in keys:
            current = values.get(key, [])
            values.update({key: current + updates})

    return take


def take_from_file(*keys):
    """ Take values from the refered file and append to the 'key' values.

    The refered file is the second argument. (So it consume two args.) """

    def take(values, iterator, _match):
        with open(iterator.next()) as handle:
            current = [line.strip() for line in handle.readlines()]
            for key in keys:
                values[key] = current

    return take


def take_as(value, *keys):
    """ Take one argument and append to the 'key' values.

    But instead of taking the argument, it takes the value as it was given. """

    def take(values, _iterator, _match):
        updates = [value]
        for key in keys:
            current = values.get(key, [])
            values.update({key: current + updates})

    return take


def take_second(*keys):
    """ Take the second argument and append to the 'key' values. """

    def take(values, iterator, _match):
        current = iterator.next()
        for key in keys:
            values[key] = current

    return take


def take_action(action):
    """ Take the action value and overwrite current value if that's bigger. """

    def take(values, _iterator, _match):
        key = 'action'
        current = values[key]
        values[key] = max(current, action)

    return take


def is_cplusplus_compiler(name):
    """ Returns true when the compiler name refer to a C++ compiler. """

    match = re.match(r'^([^/]*/)*(\w*-)*(\w+\+\+)(-(\d+(\.\d+){0,3}))?$', name)
    return False if match is None else True
