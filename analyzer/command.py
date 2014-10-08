# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import re
import os
import os.path
import sys
import copy
import shlex
from analyzer.decorators import trace, require


if 3 == sys.version_info[0]:
    NEXT = next
else:
    NEXT = lambda x: x.next()


@trace
def create(opts):
    """ From a single compilation it creates a command to run the analyzer.

    opts -- This is an entry from the compilation database plus some extra
            information, like: compiler, analyzer parameters, etc..

    The analysis is written continuation-passing like style. Each step
    takes two arguments: the current analysis state, and a method to call
    as next thing to do. (The 'opts' argument is the initial state.)

    From an input dictionary like this..

        { 'directory': ...,
          'command': ...,
          'file': ...,
          'clang': ...,
          'direct_args': ... }

    creates an output dictionary like this..

        { 'directory': ...,
          'file': ...,
          'language': ...,
          'analyze': ...,
          'report': ... }
    """

    try:
        opts.update({'command': shlex.split(opts['command'])})
        return parse(opts)
    except Exception as exception:
        logging.error(str(exception))
        return None


class Action(object):
    """ Enumeration class for compiler action. """
    Link, Compile, Preprocess, Info = range(4)


@trace
@require(['clang', 'directory', 'file', 'language', 'direct_args'])
def create_commands(opts):
    """ Create command to run analyzer or failure report generation.

    If output is passed it returns failure report command.
    If it's not given it returns the analyzer command. """
    common = []
    if 'arch' in opts:
        common.extend(['-arch', opts['arch']])
    if 'compile_options' in opts:
        common.extend(opts['compile_options'])
    common.extend(['-x', opts['language']])
    common.append(opts['file'])

    return {
        'directory': opts['directory'],
        'file': opts['file'],
        'language': opts['language'],
        'analyze': [opts['clang'], '--analyze'] + opts['direct_args'] + common,
        'report': [opts['clang'], '-fsyntax-only', '-E'] + common}


@trace
@require(['file'])
def set_language(opts, continuation=create_commands):
    """ Find out the language from command line parameters or file name
    extension. The decision also influenced by the compiler invocation. """
    def from_filename(name, is_cxx):
        mapping = {
            '.c': 'c++' if is_cxx else 'c',
            '.cp': 'c++',
            '.cpp': 'c++',
            '.cxx': 'c++',
            '.txx': 'c++',
            '.cc': 'c++',
            '.C': 'c++',
            '.ii': 'c++-cpp-output',
            '.i': 'c++-cpp-output' if is_cxx else 'c-cpp-output',
            '.m': 'objective-c',
            '.mi': 'objective-c-cpp-output',
            '.mm': 'objective-c++',
            '.mii': 'objective-c++-cpp-output'
        }
        (_, extension) = os.path.splitext(os.path.basename(name))
        return mapping.get(extension)

    accepteds = [
        'c',
        'c++',
        'objective-c',
        'objective-c++',
        'c-cpp-output',
        'c++-cpp-output',
        'objective-c-cpp-output'
    ]

    key = 'language'
    language = opts[key] if key in opts else \
        from_filename(opts['file'], opts.get('is_cxx'))
    if language is None:
        logging.debug('skip analysis, language not known')
    elif language not in accepteds:
        logging.debug('skip analysis, language not supported')
    else:
        logging.debug('analysis, language: {0}'.format(language))
        opts.update({key: language})
        return continuation(opts)
    return None


@trace
@require([])
def arch_loop(opts, continuation=set_language):
    """ Do run analyzer through one of the given architectures. """
    disableds = ['ppc', 'ppc64']

    key = 'archs_seen'
    if key in opts:
        archs = [a for a in opts[key] if '-arch' != a and a not in disableds]
        if not archs:
            logging.debug('skip analysis, found not supported arch')
            return None
        else:
            # There should be only one arch given (or the same multiple times)
            # If there are multiple arch are given, and those are not the same
            # those should not change the preprocessing step. (But that's the
            # only pass we have before run the analyzer.)
            arch = archs.pop()
            logging.debug('analysis, on arch: {0}'.format(arch))

            opts.update({'arch': arch})
            del opts[key]
            return continuation(opts)
    else:
        logging.debug('analysis, on default arch')
        return continuation(opts)


@trace
@require(['action'])
def filter_action(opts, continuation=arch_loop):
    """ Continue analysis only if it compilation or link. """
    return continuation(opts) if opts['action'] <= Action.Compile else None


@trace
@require(['command'])
def parse(opts, continuation=filter_action):
    """ Parses the command line arguments of the current invocation.

    To run analysis from a compilation command, first it disassembles the
    compilation command. Classifies the parameters into groups and throws
    away those which are not relevant. This method is doing that task.
    """
    def match(state, iterator):
        """ This method contains a list of pattern and action tuples.
            The matching start from the top if the list, when the first
            match happens the action is executed.
        """
        def regex(pattern, action):
            regexp = re.compile(pattern)

            def evaluate(iterator):
                match = regexp.match(iterator.current)
                if match:
                    action(state, iterator, match)
                    return True
            return evaluate

        def anyof(opts, action):
            def evaluate(iterator):
                if iterator.current in frozenset(opts):
                    action(state, iterator, None)
                    return True
            return evaluate

        tasks = [
            #
            regex(r'^-(E|MM?)$', take_action(Action.Preprocess)),
            anyof(['-c'], take_action(Action.Compile)),
            anyof(['-print-prog-name'], take_action(Action.Info)),
            #
            anyof(['-arch'], take_two('archs_seen')),
            #
            anyof(['-filelist'], take_from_file('files')),
            regex(r'^[^-].+', take_one('files')),
            #
            anyof(['-x'], take_second('language')),
            #
            anyof(['-o'], take_second('output')),
            #
            anyof(['-write-strings',
                   '-v'], take_one('compile_options')),
            anyof(['-ftrapv-handler',
                   '--sysroot',
                   '-target'], take_two('compile_options')),
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
            anyof(['-O'], take_as('-O1', 'compile_options')),
            anyof(['-Os'], take_as('-O2', 'compile_options')),
            regex(r'^-[DIU](.*)$', take_joined('compile_options')),
            anyof(['-nostdinc'], take_one('compile_options')),
            regex(r'^-std=', take_one('compile_options')),
            regex(r'^-include', take_two('compile_options')),
            anyof(['-idirafter',
                   '-imacros',
                   '-iprefix',
                   '-isystem',
                   '-iwithprefix',
                   '-iwithprefixbefore'], take_two('compile_options')),
            regex(r'^-m.*', take_one('compile_options')),
            regex(r'^-iquote(.*)', take_joined('compile_options')),
            regex(r'^-Wno-', take_one('compile_options')),
            # ignore
            regex(r'^-framework$', take_two()),
            regex(r'^-fobjc-link-runtime(.*)', take_joined()),
            regex(r'^-[lL]', take_one()),
            regex(r'^-M[TF]$', take_two()),
            regex(r'^-[eu]$', take_two()),
            anyof(['-fsyntax-only',
                   '-save-temps'], take_one()),
            anyof(['-install_name',
                   '-exported_symbols_list',
                   '-current_version',
                   '-compatibility_version',
                   '-init',
                   '-seg1addr',
                   '-bundle_loader',
                   '-multiply_defined',
                   '--param',
                   '--serialize-diagnostics'], take_two()),
            anyof(['-sectorder'], take_four()),
            #
            regex(r'^-[fF](.+)$', take_one('compile_options'))
        ]
        for task in tasks:
            if task(iterator):
                return

    def extend(values, key, value):
        if key in values:
            values.get(key).extend(value)
        else:
            values[key] = copy.copy(value)

    def take_n(count=1, *keys):
        def take(values, iterator, _match):
            current = []
            current.append(iterator.current)
            for _ in range(count - 1):
                current.append(iterator.next())
            for key in keys:
                extend(values, key, current)
        return take

    def take_one(*keys):
        return take_n(1, *keys)

    def take_two(*keys):
        return take_n(2, *keys)

    def take_four(*keys):
        return take_n(4, *keys)

    def take_joined(*keys):
        def take(values, iterator, match):
            current = []
            current.append(iterator.current)
            if not match.group(1):
                current.append(iterator.next())
            for key in keys:
                extend(values, key, current)
        return take

    def take_from_file(*keys):
        def take(values, iterator, _match):
            with open(iterator.next()) as handle:
                current = [line.strip() for line in handle.readlines()]
                for key in keys:
                    values[key] = current
        return take

    def take_as(value, *keys):
        def take(values, _iterator, _match):
            current = [value]
            for key in keys:
                extend(values, key, current)
        return take

    def take_second(*keys):
        def take(values, iterator, _match):
            current = iterator.next()
            for key in keys:
                values[key] = current
        return take

    def take_action(action):
        def take(values, _iterator, _match):
            key = 'action'
            current = values[key]
            values[key] = max(current, action)
        return take

    def is_cxx(cmd):
        m = re.match(r'([^/]*/)*(\w*-)*(\w+\+\+)(-(\d+(\.\d+){0,3}))?$', cmd)
        return False if m is None else True

    class ArgumentIterator(object):
        """ Iterator from the current value can be queried. """
        def __init__(self, args):
            self.current = None
            self.__it = iter(args)

        def next(self):
            self.current = NEXT(self.__it)
            return self.current

    state = {'action': Action.Link}
    try:
        command = opts['command']
        # get the invocation intent
        state.update(is_cxx=is_cxx(command[0]))
        # iterate on arguments
        iterator = ArgumentIterator(command[1:])
        while True:
            iterator.next()
            match(state, iterator)
    except StopIteration:
        del opts['command']
        state.update(opts)
        return continuation(state)
