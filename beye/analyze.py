# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import subprocess
import logging
import six
import re


_CompileOptionMap = {
    '-nostdinc': 0,
    '-include': 1,
    '-idirafter': 1,
    '-imacros': 1,
    '-iprefix': 1,
    '-iquote': 1,
    '-isystem': 1,
    '-iwithprefix': 1,
    '-iwithprefixbefore': 1,
    '-std': 1
}

_LinkerOptionMap = {
    '-framework': 1,
    '-fobjc-link-runtime': 0
}

_CompilerLinkerOptionMap = {
    '-Wwrite-strings': 0,
    '-ftrapv-handler': 1,  # specifically call out separated -f flag
    '-mios-simulator-version-min': 1,
    '-isysroot': 1,
    '-m32': 0,
    '-m64': 0,
    '-stdlib': 1,
    '-target': 1,
    '-v': 0,
    '-mmacosx-version-min': 1,
    '-miphoneos-version-min': 1
}

_IgnoredOptionMap = {
    '-MT': 1,
    '-MF': 1,
    '-fsyntax-only': 0,
    '-save-temps': 0,
    '-install_name': 1,
    '-exported_symbols_list': 1,
    '-current_version': 1,
    '-compatibility_version': 1,
    '-init': 1,
    '-e': 1,
    '-seg1addr': 1,
    '-bundle_loader': 1,
    '-multiply_defined': 1,
    '-sectorder': 3,
    '--param': 1,
    '-u': 1,
    '--serialize-diagnostics': 1
}

_LangMap = {
    'c': 'c',
    'cp': 'c++',
    'cpp': 'c++',
    'cxx': 'c++',
    'txx': 'c++',
    'cc': 'c++',
    'C': 'c++',
    'ii': 'c++',
    'i': 'c-cpp-output',
    'm': 'objective-c',
    'mi': 'objective-c-cpp-output',
    'mm': 'objective-c++'
}

_UniqueOptions = {
    '-isysroot': 0
}

_LangsAccepted = {
    "c": 1,
    "c++": 1,
    "objective-c": 1,
    "objective-c++": 1
}

_DisabledArchs = {
    'ppc': 1,
    'ppc64': 1
}


class Action:
    Link, Compile, Preprocess, Info = range(4)


class Iterator:
    def __init__(self, args):
        self.current = None
        self.__it = iter(args)

    def next(self):
        self.current = six.next(self.__it)
        return self.current


def parse(args):
    def extend(values, key, value):
        if key in values:
            values.get(key).extend(value)
        else:
            values[key] = value

    def take_one(*keys):
        def take(values, it, _m):
            current = []
            current.append(it.current)
            for key in keys:
                extend(values, key, current)
        return take

    def take_two(*keys):
        def take(values, it, _m):
            current = []
            current.append(it.current)
            current.append(it.next())
            for key in keys:
                extend(values, key, current)
        return take

    def take_joined(*keys):
        def take(values, it, match):
            current = []
            current.append(it.current)
            if '' == match.group(1):
                current.append(it.next())
            for key in keys:
                extend(values, key, current)
        return take

    def take_action(action):
        def take(values, _it, _m):
            key = 'action'
            current = values.get(key, Action.Link)
            values[key] = max(current, action)
        return take

    def match(state, it):
        task_map = [
            (re.compile('^-nostdinc$'), take_one('compile_options')),
            (re.compile('^-include'), take_two('compile_options')),
            (re.compile('^-idirafter$'), take_two('compile_options')),
            (re.compile('^-imacros$'), take_two('compile_options')),
            (re.compile('^-c$'), take_action(Action.Compile)),
            (re.compile('^-M[TF]$'), take_two())
        ]
        for pattern, task in task_map:
            match = pattern.match(it.current)
            if match is not None:
                task(state, it, match)
                return

    state = dict()
    try:
        it = Iterator(args[1:])
        while True:
            it.next()
            match(state, it)
    except:
        return state


class Options:
    def __init__(self):
        self.actions = [Action.Link]
        self.archs_seen = []
        self.compile_options = []
        self.link_options = []
        self.language = None
        self.output = None
        self.files = []

    def get_action(self):
        return max(self.actions)

    def read_files_from(self, fname):
        with open(fname) as f:
            self.files = f.readlines()


class Parser:

    @staticmethod
    def run(args):
        state = Options()
        try:
            it = iter(Parser.split_arguments(args)[1:])
            while True:
                Parser.__loop__(state, it)
        except:
            return state

    @staticmethod
    def __loop__(state, it):
        current = six.next(it)
        # collect action related switches
        if re.match('^-print-prog-name', current):
            state.actions.append(Action.Info)
        elif re.match('^-(E|MM?)$', current):
            state.actions.append(Action.Preprocess)
        elif '-c' == current:
            state.actions.append(Action.Compile)
        # ignore some options
        ignored_option = _IgnoredOptionMap.get(current)
        if ignored_option is not None:
            for i in range(both_option):
                six.next(it)
            return
        # collect arch flags
        if '-arch' == current:
            state.archs_seen.append(six.next(it))
            return
        # collect compile flags
        compiler_option = _CompileOptionMap.get(current)
        if compiler_option is not None:
            state.compile_options.append(current)
            for i in range(compiler_option):
                state.compile_options.append(six.next(it))
            return
        if re.match('^-m.*', current):
            state.compile_options.append(current)
            return
        if re.match('^-iquote.*', current):
            state.compile_options.append(current)
            return
        # collect linker flags
        link_option = _LinkerOptionMap.get(current)
        if link_option is not None:
            state.link_options.append(current)
            for i in range(link_option):
                state.link_options.append(six.next(it))
            return
        # collect compile and linker flags
        both_option = _CompilerLinkerOptionMap.get(current)
        if both_option is not None:
            both_options = []
            both_options.append(current)
            for i in range(both_option):
                both_options.append(six.next(it))
            state.compile_options.extend(both_options)
            state.link_options.extend(both_options)
            return
        # collect compile mode flags
        mode_match = re.match('^-[D,I,U](.*)$', current)
        if mode_match:
            state.compile_options.append(current)
            if '' == mode_match.group(1):
                state.compile_options.append(six.next(it))
            return
        # collect language
        if '-x' == current:
            state.language = six.next(it)
            return
        # collect output file
        if '-o' == current:
            state.output = six.next(it)
            return
        # collect link mode
        if re.match('^-[l,L,O]', current):
            if '-O' == current:
                state.link_options.append('-O1')
            elif '-Os' == current:
                state.link_options.append('-O2')
            else:
                state.link_options.append(current)
            # optimalization must pass for __OPTIMIZE__ macro
            if re.match('^-O', current):
                state.compile_options.append(current)
            return
        # collect compiler/link mode
        mode_match = re.match('^-F(.+)$', current)
        if mode_match:
            both_options = []
            both_options.append(current)
            if '' == mode_match.group(1):
                both_options.append(six.next(it))
            state.compile_options.extend(both_options)
            state.link_options.extend(both_options)
            return
        # input files
        if '-filelist' == current:
            state.read_files_from(six.next(it))
            return
        # collect other control flags
        if re.match('^-f', current):
            state.compile_options.append(current)
            state.link_options.append(current)
            return
        # collect some warning flags
        if re.match('^-Wno-', current):
            state.compile_options.append(current)
            return
        # collect input files
        if not (re.match('^-', current)):
            state.files.append(current)
            return

    @staticmethod
    def split_arguments(args):
        return [val for subl in [a.split('=') for a in args] for val in subl]


class Analyzer:
    def run(self, **keywords):
        import os
        input = keywords['task']
        cmd = input['command'].split(' ')
        cmd[0] = '/usr/lib/clang-analyzer/scan-build/ccc-analyzer'
        os.environ['CCC_ANALYZER_HTML'] = keywords.get('html_dir')
        logging.debug('executing: {}'.format(cmd))
        compilation = subprocess.Popen(cmd, env=os.environ)
        compilation.wait()
        return compilation.returncode
