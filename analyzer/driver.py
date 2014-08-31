# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import subprocess
import logging
import re
import os
import os.path
import sys
import tempfile
import copy
import functools
import shlex
from analyzer.decorators import trace, require
from analyzer.clang import get_arguments, get_version


@trace
def run(opts):
    """ Driver method to run the analyzer against a single file.

    opts -- a dictionary about to run an analysis. It contains all needed
            information, like: source file, working directory, compilation
            command lines (these are from the compilation database). And
            compiler, output directory, analyzer parameters, etc..

    The analysis is written continuation-passing like style. Each step
    takes two arguments: the current analysis state, and a method to call
    as next thing to do. (The 'opts' argument is the initial state.)

    Continuations might require certain attribute(s) present in the state.
    Those are checked with a decorator 'require'.
    """

    def chain(conts):
        """ Creates a single method from multiple continuations.

        This method takes an array of those functions and build a single
        method wich takes only one argument, the state. """
        def bind(cs, acc):
            return bind(cs[1:], lambda x: cs[0](x, acc)) if cs else acc

        conts.reverse()
        return bind(conts, lambda x: x)

    method = chain([parse,
                   filter_action,
                   arch_loop,
                   set_language,
                   set_analyzer_output,
                   run_analyzer,
                   report_failure])

    try:
        return method({k: v for k, v in opts.items() if v is not None})
    except Exception as exception:
        logging.error(str(exception))
        return None


class Action(object):
    """ Enumeration class for compiler action. """
    Link, Compile, Preprocess, Info = range(4)


@trace
@require(['command'])
def parse(opts, continuation):
    """ Parses the command line arguments of the current invocation.

    To run analysis from a compilation command, first it disassembles the
    compilation command. Classifies the parameters into groups and throws
    away those which are not relevant. This method is doing that task.
    """
    def match(state, it):
        """ This method contains a list of pattern and action tuples.
            The matching start from the top if the list, when the first
            match happens the action is executed.
        """
        def regex(pattern, action):
            regexp = re.compile(pattern)

            def evaluate(it):
                match = regexp.match(it.current)
                if match:
                    action(state, it, match)
                    return True
            return evaluate

        def anyof(opts, action):
            def evaluate(it):
                if it.current in frozenset(opts):
                    action(state, it, None)
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
            if task(it):
                return

    def extend(values, key, value):
        if key in values:
            values.get(key).extend(value)
        else:
            values[key] = copy.copy(value)

    def take_n(n=1, *keys):
        def take(values, it, _match):
            current = []
            current.append(it.current)
            for _ in range(n - 1):
                current.append(it.next())
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
        def take(values, it, match):
            current = []
            current.append(it.current)
            if not match.group(1):
                current.append(it.next())
            for key in keys:
                extend(values, key, current)
        return take

    def take_from_file(*keys):
        def take(values, it, _match):
            with open(it.next()) as f:
                current = [l.strip() for l in f.readlines()]
                for key in keys:
                    values[key] = current
        return take

    def take_as(value, *keys):
        def take(values, _it, _match):
            current = [value]
            for key in keys:
                extend(values, key, current)
        return take

    def take_second(*keys):
        def take(values, it, _match):
            current = it.next()
            for key in keys:
                values[key] = current
        return take

    def take_action(action):
        def take(values, _it, _match):
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
            self.current = next(self.__it) if 3 == sys.version_info[0] \
                else self.__it.next()
            return self.current

    state = {'action': Action.Link}
    try:
        # split command line if needed
        command = opts['command']
        if isinstance(command, str):
            command = shlex.split(command)
        # get the invocation intent
        state.update(is_cxx=is_cxx(command[0]))
        # iterate on arguments
        it = ArgumentIterator(command[1:])
        while True:
            it.next()
            match(state, it)
    except StopIteration:
        del opts['command']
        state.update(opts)
        return continuation(state)


@trace
@require(['action'])
def filter_action(opts, continuation):
    """ Continue analysis only if it compilation or link. """
    return continuation(opts) if opts['action'] <= Action.Compile else None


@trace
@require([])
def arch_loop(opts, continuation):
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
@require(['file'])
def set_language(opts, continuation):
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
def set_analyzer_output(opts, continuation):
    """ Create output file if was requested.

    This plays a role only if .plist files are requested. """
    def needs_output_file():
        output_format = opts.get('output_format')
        return 'plist' == output_format or 'plist-html' == output_format

    if needs_output_file():
        with tempfile.NamedTemporaryFile(prefix='report-',
                                         suffix='.plist',
                                         delete='html_dir' not in opts,
                                         dir=opts.get('html_dir')) as output:
            opts.update({'analyzer_output': output.name})
            return continuation(opts)
    else:
        return continuation(opts)


@trace
@require(['language', 'directory', 'file', 'clang'])
def run_analyzer(opts, continuation):
    """ From the state parameter it assembles the analysis command line and
    executes it. Capture the output of the analysis and returns with it. If
    failure reports are requested, it calls the continuation to generate it.
    """
    cwd = opts['directory']
    cmd = build_args(opts)
    logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
    child = subprocess.Popen(cmd,
                             cwd=cwd,
                             universal_newlines=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    output = child.stdout.readlines()
    # do report details if it were asked
    child.wait()
    if 'report_failures' in opts and child.returncode:
        error_type = 'crash' if child.returncode & 127 else 'other_error'
        opts.update(
            {'error_type': error_type,
             'error_output': output,
             'exit_code': child.returncode})
        return continuation(opts)
    return {'analyzer': {'error_output': output,
                         'exit_code': child.returncode},
            'file': opts['file']}


@trace
@require(['language',
          'directory',
          'file',
          'clang',
          'uname',
          'html_dir',
          'error_type',
          'error_output',
          'exit_code'])
def report_failure(opts, _):
    """ Create report when analyzer failed.

    The major report is the preprocessor output. The output filename generated
    randomly. The compiler output also captured into '.stderr.txt' file. And
    some more execution context also saved into '.info.txt' file.
    """
    def extension(opts):
        """ Generate preprocessor file extension. """
        mapping = {
            'objective-c++': '.mii',
            'objective-c': '.mi',
            'c++': '.ii'
        }
        return mapping.get(opts['language'], '.i')

    def destination(opts):
        """ Creates failures directory if not exits yet. """
        name = os.path.join(opts['html_dir'], 'failures')
        if not os.path.isdir(name):
            os.makedirs(name)
        return name

    error = opts['error_type']
    (handle, name) = tempfile.mkstemp(suffix=extension(opts),
                                      prefix='clang_' + error + '_',
                                      dir=destination(opts))
    os.close(handle)
    cwd = opts['directory']
    cmd = get_arguments(cwd, build_args(opts, name))
    logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
    subprocess.call(cmd, cwd=cwd)

    with open(name + '.info.txt', 'w') as handle:
        handle.write(os.path.abspath(opts['file']) + os.linesep)
        handle.write(error.title().replace('_', ' ') + os.linesep)
        handle.write(' '.join(cmd) + os.linesep)
        handle.write(opts['uname'])
        handle.write(get_version(cmd[0]))
        handle.close()

    with open(name + '.stderr.txt', 'w') as handle:
        handle.writelines(opts['error_output'])
        handle.close()

    return {'analyzer': {'error_output': opts['error_output'],
                         'exit_code': opts['exit_code']},
            'file': opts['file']}


@trace
def build_args(opts, output=None):
    """ Create command to run analyzer or failure report generation.

    If output is passed it returns failure report command.
    If it's not given it returns the analyzer command. """
    def syntax_check():
        result = []
        if 'arch' in opts:
            result.extend(['-arch', opts['arch']])
        if 'compile_options' in opts:
            result.extend(opts['compile_options'])
        result.extend(['-x', opts['language']])
        result.append(opts['file'])
        return result

    def implicit_output():
        result = []
        if 'analyzer_output' in opts:
            result.extend(['-o', opts['analyzer_output']])
        elif 'html_dir' in opts:
            result.extend(['-o', opts['html_dir']])
        return result

    def static_analyzer():
        result = []
        if 'store_model' in opts:
            result.append('-analyzer-store={0}'.format(opts['store_model']))
        if 'constraints_model' in opts:
            result.append(
                '-analyzer-constraints={0}'.format(opts['constraints_model']))
        if 'internal_stats' in opts:
            result.append('-analyzer-stats')
        if 'enable_checker' in opts:
            result = functools.reduce(
                lambda acc, x: acc + ['-analyzer-checker', x],
                opts['enable_checker'],
                result)
        if 'disable_checker' in opts:
            result = functools.reduce(
                lambda acc, x: acc + ['-analyzer-disable-checker', x],
                opts['disable_checker'],
                result)
        if 'analyze_headers' in opts:
            result.append('-analyzer-opt-analyze-headers')
        if 'stats' in opts:
            result.append('-analyzer-checker=debug.Stats')
        if 'maxloop' in opts:
            result.extend(['-analyzer-max-loop', str(opts['maxloop'])])
        if 'output_format' in opts:
            result.append('-analyzer-output={0}'.format(opts['output_format']))
        if 'analyzer_config' in opts:
            result.append(opts['analyzer_config'])
        if 'verbose' in opts and 2 <= opts['verbose']:
            result.append('-analyzer-display-progress')
        if 'ubiviz' in opts:
            result.append('-analyzer-viz-egraph-ubigraph')
        return functools.reduce(
            lambda acc, x: acc + ['-Xclang', x], result, [])

    if output:
        return [opts['clang'], '-fsyntax-only', '-E', '-o', output] + \
            syntax_check()
    else:
        return [opts['clang'], '--analyze'] + \
            syntax_check() + static_analyzer() + implicit_output()
