# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import subprocess
import logging


_CompileOptionMap = {
    '-nostdinc': 0,
    '-include': 1,
    '-idirafter': 1,
    '-imacros': 1,
    '-iprefix': 1,
    '-iquote': 1,
    '-isystem': 1,
    '-iwithprefix': 1,
    '-iwithprefixbefore': 1
}

_LinkerOptionMap = {
    '-framework': 1,
    '-fobjc-link-runtime': 0
}

_CompilerLinkerOptionMap = {
    '-Wwrite-strings': 0,
    # specifically call out separated -f flag
    '-ftrapv-handler': 1,
    # This is really a 1 argument, but always has '='
    '-mios-simulator-version-min': 0,
    '-isysroot': 1,
    '-arch': 1,
    '-m32': 0,
    '-m64': 0,
    # This is really a 1 argument, but always has '='
    '-stdlib': 0,
    '-target': 1,
    '-v': 0,
    # This is really a 1 argument, but always has '='
    '-mmacosx-version-min': 0,
    # This is really a 1 argument, but always has '='
    '-miphoneos-version-min': 0
}

_IgnoredOptionMap = {
    '-MT': 1,  # Ignore these preprocessor options.
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
    Info, Link, Compile, Preprocess = range(4)

    import re
    __preprocess_regex = re.compile('^-(E|MM?)$')
    __info_regex = re.compile('^-print-prog-name')

    @staticmethod
    def parse(args):
        result = Action.Link
        for arg in args:
            if (Action.__info_regex.match(arg)):
                return Action.Info
            elif (Action.__preprocess_regex.match(arg)):
                return Action.Preprocess
            elif ('-c' == arg):
                result = Action.Compile
        return result


def split_arguments(args):
    def flatten(arg):
        return [val for subl in arg for val in subl]

    return flatten([a.split('=') for a in args])


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
