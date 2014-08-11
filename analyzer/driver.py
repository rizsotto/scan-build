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


@trace
def run(opts):
    def stack(conts):
        """ Creates a single method from multiple continuations.

        The analysis is written continuation-passing like style.
        Each step takes two arguments: the current analysis state,
        and a method to call as next thing to do.

        This method takes an array of those functions and build
        a single method wich takes only one argument, the state. """
        def bind(cs, acc):
            return bind(cs[1:], lambda x: cs[0](x, acc)) if cs else acc

        conts.reverse()
        return bind(conts, lambda x: x)

    chain = stack([parse,
                   filter_action,
                   arch_loop,
                   set_language,
                   set_analyzer_output,
                   run_analyzer,
                   report_failure])

    return chain(opts)


def filter_dict(original, removables, additions):
    """ Utility function to isolate changes on dictionaries.

    It only creates shallow copy of the input dictionary. So, modifying
    values are not isolated. But to remove and add new ones are safe.
    """
    new = dict()
    for (k, v) in original.items():
        if v and k not in removables:
            new[k] = v
    for (k, v) in additions.items():
        new[k] = v
    return new


def check_output(*popenargs, **kwargs):
    """ python 2.6 does not have subprocess.check_output method. """
    if "check_output" in dir(subprocess):
        return subprocess.check_output(*popenargs, **kwargs)

    if 'stdout' in kwargs:
        raise ValueError('stdout argument will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, _ = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd)
    return output


class Action(object):
    """ Enumeration class for compiler action. """
    Link, Compile, Preprocess, Info = range(4)


@trace
@require(['command'])
def parse(opts, continuation):
    """ Parses the command line arguments of the current invocation. """
    def match(state, it):
        """ This method contains a list of pattern and action tuples.
            The matching start from the top if the list, when the first
            match happens the action is executed.
        """
        def regex(pattern, action):
            regexp = re.compile(pattern)

            def eval(it):
                match = regexp.match(it.current)
                if match:
                    action(state, it, match)
                    return True
            return eval

        def anyof(opts, action):
            def eval(it):
                if it.current in frozenset(opts):
                    action(state, it, None)
                    return True
            return eval

        tasks = [
            #
            regex('^-(E|MM?)$', take_action(Action.Preprocess)),
            anyof(['-c'], take_action(Action.Compile)),
            anyof(['-print-prog-name'], take_action(Action.Info)),
            #
            anyof(['-arch'], take_two('archs_seen')),
            #
            anyof(['-filelist'], take_from_file('files')),
            regex('^[^-].+', take_one('files')),
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
            regex('^-isysroot', take_two('compile_options')),
            regex('^-m(32|64)$', take_one('compile_options')),
            regex('^-mios-simulator-version-min(.*)',
                  take_joined('compile_options')),
            regex('^-stdlib(.*)', take_joined('compile_options')),
            regex('^-mmacosx-version-min(.*)', take_joined('compile_options')),
            regex('^-miphoneos-version-min(.*)',
                  take_joined('compile_options')),
            regex('^-O[1-3]$', take_one('compile_options')),
            anyof(['-O'], take_as('-O1', 'compile_options')),
            anyof(['-Os'], take_as('-O2', 'compile_options')),
            regex('^-[DIU](.*)$', take_joined('compile_options')),
            anyof(['-nostdinc'], take_one('compile_options')),
            regex('^-std=', take_one('compile_options')),
            regex('^-include', take_two('compile_options')),
            anyof(['-idirafter',
                   '-imacros',
                   '-iprefix',
                   '-isystem',
                   '-iwithprefix',
                   '-iwithprefixbefore'], take_two('compile_options')),
            regex('^-m.*', take_one('compile_options')),
            regex('^-iquote(.*)', take_joined('compile_options')),
            regex('^-Wno-', take_one('compile_options')),
            # ignore
            regex('^-framework$', take_two()),
            regex('^-fobjc-link-runtime(.*)', take_joined()),
            regex('^-[lL]', take_one()),
            regex('^-M[TF]$', take_two()),
            regex('^-[eu]$', take_two()),
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
            regex('^-[fF](.+)$', take_one('compile_options'))
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
        it = ArgumentIterator(opts['command'][1:])
        while True:
            it.next()
            match(state, it)
    except StopIteration:
        return continuation(filter_dict(opts, frozenset(['command']), state))
    except:
        logging.exception('parsing failed')


@trace
@require(['action'])
def filter_action(opts, continuation):
    """ Continue analysis only if it compilation or link. """
    return continuation(opts) if opts['action'] <= Action.Compile else 0


@trace
@require()
def arch_loop(opts, continuation):
    disableds = ['ppc', 'ppc64']

    key = 'archs_seen'
    result = 0
    if key in opts:
        archs = [a for a in opts[key] if '-arch' != a and a not in disableds]
        if not archs:
            logging.info('skip analysis, found not supported arch')
        else:
            for arch in archs:
                logging.info('analysis, on arch: {0}'.format(arch))
                result += continuation(
                    filter_dict(opts, frozenset([key]), {'arch': arch}))
    else:
        logging.info('analysis, on default arch')
        result = continuation(opts)
    return result


@trace
@require(['file'])
def set_language(opts, continuation):
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
        logging.info('skip analysis, language not known')
    elif language not in accepteds:
        logging.info('skip analysis, language not supported')
    else:
        logging.info('analysis, language: {0}'.format(language))
        return continuation(
            filter_dict(opts, frozenset([key]), {key: language}))
    return 0


@trace
@require()
def set_analyzer_output(opts, continuation):
    """ Create output file if was requested. """
    class TempFile(object):
        """ Temporary file destroyed on exit, when it's empty. """
        def __init__(self, html_dir):
            (self.handle, self.name) = tempfile.mkstemp(suffix='.plist',
                                                        prefix='report-',
                                                        dir=html_dir)
            logging.info('analyzer output: {0}'.format(self.name))

        def __enter__(self):
            return self.name

        def __exit__(self, exc, value, tb):
            try:
                os.close(self.handle)
                if 0 == os.stat(self.name).st_size:
                    os.remove(self.name)
            except:
                logging.warning('cleanup failed on {0}'.format(self.name))

    if 'plist' == opts.get('output_format') and 'html_dir' in opts:
        with TempFile(opts['html_dir']) as output:
            return continuation(
                filter_dict(opts, frozenset(), {'analyzer_output': output}))
    return continuation(opts)


@trace
@require(['language', 'directory', 'file', 'clang'])
def run_analyzer(opts, continuation):
    cwd = opts['directory']
    cmd = get_clang_arguments(cwd, build_args(opts))
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
        return continuation(
            filter_dict(opts,
                        frozenset(),
                        {'error_type': error_type,
                         'error_output': output,
                         'exit_code': child.returncode}))
    return child.returncode


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
        name = os.path.abspath(opts['html_dir'] + os.sep + 'failures')
        if not os.path.isdir(name):
            os.makedirs(name)
        return name

    error = opts['error_type']
    (handle, name) = tempfile.mkstemp(suffix=extension(opts),
                                      prefix='clang_' + error + '_',
                                      dir=destination(opts))
    os.close(handle)
    cwd = opts['directory']
    cmd = get_clang_arguments(cwd, build_args(opts, name))
    logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
    subprocess.call(cmd, cwd=cwd)

    with open(name + '.info.txt', 'w') as handle:
        handle.write(os.path.abspath(opts['file']) + os.linesep)
        handle.write(error.title().replace('_', ' ') + os.linesep)
        handle.write(' '.join(cmd) + os.linesep)
        handle.write(opts['uname'])
        handle.write(
            check_output([cmd[0], '-v'],
                         stderr=subprocess.STDOUT).decode('ascii'))
        handle.close()

    with open(name + '.stderr.txt', 'w') as handle:
        handle.writelines(opts['error_output'])
        handle.close()

    return opts['exit_code']


@trace
def get_clang_arguments(cwd, cmd):
    """ Capture Clang invocation.

    Clang can be executed directly (when you just ask specific action to
    execute) or indidect way (whey you first ask Clang to print the command
    to run for that compilation, and then execute the given command).

    This method receives the full command line for direct compilation. And
    it generates the command for indirect compilation.
    """
    def lastline(stream):
        last = None
        for line in stream:
            last = line
        if last is None:
            raise Exception("output not found")
        return last

    def strip_quotes(quoted):
        match = re.match('^\"([^\"]*)\"$', quoted)
        return match.group(1) if match else quoted

    try:
        cmd.insert(1, '-###')
        logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
        child = subprocess.Popen(cmd,
                                 cwd=cwd,
                                 universal_newlines=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        line = lastline(child.stdout)
        child.wait()
        if 0 == child.returncode:
            if re.match('^clang: error:', line):
                raise Exception(line)
            return [strip_quotes(x) for x in shlex.split(line)]
        else:
            raise Exception(line)
    except Exception as e:
        logging.error('failed to get clang arguments: {0}'.format(str(e)))
        return None


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
        if 'analyses' in opts:
            result.extend(opts['analyses'])
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
