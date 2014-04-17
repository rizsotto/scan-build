# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import subprocess
import logging
import six
import re
import os
import os.path
import sys
import tempfile
import copy
import functools
import shlex


class Action:
    Link, Compile, Preprocess, Info = range(4)


""" This method groups the command line arguments of the compiler.

    The arguments suppose to be clang arguments. The result is a
    dictionary, with the key of the group and the value as a list
    of arguments which belongs to that group.
"""
def parse(args):
    """ This method contains a list of pattern and action tuples.
        The matching start from the top if the list, when the first
        match happens the action is executed.
    """
    def match(state, it):
        def regex(pattern, action):
            regexp = re.compile(pattern)

            def eval(it):
                match = regexp.match(it.current)
                if match:
                    action(state, it, match)
                    return True
            return eval

        def anyof(opts, action):
            params = frozenset(opts) if six.PY3 else set(opts)

            def eval(it):
                if it.current in params:
                    action(state, it, None)
                    return True
            return eval

        tasks = [
            #
            regex('^-(E|MM?)$', take_action(Action.Preprocess)),
            anyof(['-c'], take_action(Action.Compile)),
            anyof(['-print-prog-name'], take_action(Action.Info)),
            #
            anyof(['-arch'], take_two('archs_seen', 'compile_options',
                                      'link_options')),
            #
            anyof(['-filelist'], take_from_file('files')),
            regex('^[^-].+', take_one('files')),
            #
            anyof(['-x'], take_second('language')),
            #
            anyof(['-o'], take_second('output')),
            #
            anyof(['-write-strings',
                   '-v'], take_one('compile_options', 'link_options')),
            anyof(['-ftrapv-handler',
                   '-target'], take_two('compile_options', 'link_options')),
            regex('^-isysroot', take_two('compile_options', 'link_options')),
            regex('^-m(32|64)$', take_one('compile_options', 'link_options')),
            regex('^-mios-simulator-version-min(.*)',
                  take_joined('compile_options', 'link_options')),
            regex('^-stdlib(.*)',
                  take_joined('compile_options', 'link_options')),
            regex('^-mmacosx-version-min(.*)',
                  take_joined('compile_options', 'link_options')),
            regex('^-miphoneos-version-min(.*)',
                  take_joined('compile_options', 'link_options')),
            regex('^-O[1-3]$', take_one('compile_options', 'link_options')),
            anyof(['-O'], take_as('-O1', 'compile_options', 'link_options')),
            anyof(['-Os'], take_as('-O2', 'compile_options', 'link_options')),
            #
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
            #
            regex('^-framework$', take_two('link_options')),
            regex('^-fobjc-link-runtime(.*)', take_joined('link_options')),
            regex('^-[lL]', take_one('link_options')),
            # ignore
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
                   '-sectorder',
                   '--param',
                   '--serialize-diagnostics'], take_two()),
            #
            regex('^-[fF](.+)$', take_one('compile_options', 'link_options'))
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
        def take(values, it, _m):
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
        def take(values, it, _m):
            with open(it.next()) as f:
                current = [l.strip() for l in f.readlines()]
                for key in keys:
                    values[key] = current
        return take

    def take_as(value, *keys):
        def take(values, it, _m):
            current = [value]
            for key in keys:
                extend(values, key, current)
        return take

    def take_second(*keys):
        def take(values, it, _m):
            current = it.next()
            for key in keys:
                values[key] = current
        return take

    def take_action(action):
        def take(values, _it, _m):
            key = 'action'
            current = values[key]
            values[key] = max(current, action)
        return take

    class ArgumentIterator:
        def __init__(self, args):
            self.current = None
            self.__it = iter(args)

        def next(self):
            self.current = six.next(self.__it)
            return self.current

    state = { 'action': Action.Link }
    try:
        it = ArgumentIterator(args[1:])
        while True:
            it.next()
            match(state, it)
    except StopIteration:
        return state
    except:
        logging.exception('parsing failed')


""" Utility function to isolate changes on dictionaries.

    It only creates shallow copy of the input dictionary. So, modifying
    values are not isolated. But to remove and add new ones are safe.
"""
def filter_dict(original, removables, additions):
    new = dict()
    for (k, v) in original.items():
        if v and k not in removables:
            new[k] = v
    for (k, v) in additions.items():
        new[k] = v
    return new


""" Main method to run the analysis.

    The analysis is written a lightweight continuation style. Each step
    takes two arguments: the command line options grouped by the parse
    method, and the continuation to call on success.
"""
def run(**kwargs):
    def stack(conts):
        def bind(cs, acc):
            return bind(cs[1:], lambda x: cs[0](x, acc)) if cs else acc

        conts.reverse()
        return bind(conts, lambda x: x)

    chain = stack([filter_action,
                  arch_loop,
                  files_loop,
                  set_language,
                  set_analyzer_output,
                  run_analyzer])

    opts = parse(shlex.split(kwargs['command']))
    return chain(filter_dict(kwargs, frozenset(['command']), opts))


""" Trace utilities to simplify debugging.
"""
def trace(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        logging.debug('entering {0}'.format(fn.__name__))
        result = fn(*args, **kwargs)
        logging.debug('leaving {0}'.format(fn.__name__))
        return result

    return wrapper


def continuation(fn):
    @functools.wraps(fn)
    def wrapper(opts, cont):
        logging.debug('opts {0}'.format(opts))
        result = fn(opts, cont)
        return result

    return wrapper


""" Continue analysis only if it compilation or link.
"""
@trace
@continuation
def filter_action(opts, continuation):
    return continuation(opts) if opts['action'] <= Action.Compile else 0


@trace
@continuation
def arch_loop(opts, continuation):
    disableds = ['ppc', 'ppc64']

    key = 'archs_seen'
    if key in opts:
        archs = [a for a in opts[key] if '-arch' != a and a not in disableds]
        if archs:
            for arch in archs:
                logging.debug('  analysis, on arch: {0}'.format(arch))
                status = continuation(filter_dict(opts, set([key]), {'arch': arch}))
                if status != 0:
                    return status
        else:
            logging.debug('skip analysis, found not supported arch')
            return 0
    else:
        logging.debug('  analysis, on default arch')
        return continuation(opts)


@trace
@continuation
def files_loop(opts, continuation):
    if 'files' in opts:
        for fn in opts['files']:
            logging.debug('  analysis, source file: {0}'.format(fn))
            status = continuation(filter_dict(opts, frozenset(['files']), {'file': fn}))
            if status != 0:
                return status
    else:
        logging.debug('skip analysis, source file not found')
        return 0


@trace
@continuation
def set_language(opts, continuation):
    def from_filename(fn, isCxx):
        mapping = {
          '.c'   : 'c++' if isCxx else 'c',
          '.cp'  : 'c++',
          '.cpp' : 'c++',
          '.cxx' : 'c++',
          '.txx' : 'c++',
          '.cc'  : 'c++',
          '.C'   : 'c++',
          '.ii'  : 'c++-cpp-output',
          '.i'   : 'c++-cpp-output' if isCxx else 'c-cpp-output',
          '.m'   : 'objective-c',
          '.mi'  : 'objective-c-cpp-output',
          '.mm'  : 'objective-c++',
          '.mii' : 'objective-c++-cpp-output'
        }
        (_, extension) = os.path.splitext(os.path.basename(fn))
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
    language = opts[key] if key in opts else from_filename(opts['file'], opts.get('isCxx'))
    if language is None:
        logging.debug('skip analysis, language not known')
    elif language not in accepteds:
        logging.debug('skip analysis, language not supported')
    else:
        logging.debug('  analysis, language: {0}'.format(language))
        return continuation(filter_dict(opts, set([key]), {key: language}))
    return 0


@trace
@continuation
def set_analyzer_output(opts, continuation):
    @trace
    def create_analyzer_output():
        (fd, name) = tempfile.mkstemp(suffix='.plist',
                                      prefix='report-',
                                      dir=opts.get('html_dir'))
        os.close(fd)
        logging.debug('analyzer output: {0}'.format(name))
        return name

    @trace
    def cleanup_when_needed(fn):
        try:
            if 'html_dir' not in opts or os.stat(fn).st_size == 0:
                os.remove(fn)
        except:
            logging.warning('cleanup on analyzer output failed {0}'.format(fn))

    key = 'output_format'
    if key in opts and 'plist' == opts[key]:
        fn = create_analyzer_output()
        status = continuation(filter_dict(opts, frozenset(), {'analyzer_output': fn}))
        cleanup_when_needed(fn)
        return status
    return continuation(opts)


@trace
@continuation
def run_analyzer(opts, continuation):
    (regular_parsing_args, analysis_args) = build_args(opts)
    cwd = opts.get('directory', os.getcwd())
    clang = 'clang++' if opts.get('isCxx') else 'clang'
    syntax_args = get_clang_arguments(cwd, clang, '-fsyntax-only', regular_parsing_args)
    final_args = get_clang_arguments(cwd, clang, '--analyze', analysis_args)
    report = process_clang_failure(cwd, syntax_args, opts)
    continuation(exec_analyzer(cwd, final_args, opts, report))


class ErrorType:
    Crash, ParserRejects, AttributeIgnored, OtherError = range(4)


def process_clang_failure(cwd, cmd, opts):
    def preprocessor_ext(language):
        mapping = {
            'objective-c++' : '.mii',
            'objective-c'   : '.mi',
            'c++'           : '.ii'
        }
        return mapping.get(language, '.i')

    def failure_dir(opts):
        name = os.path.abspath(opts.get('html_dir') + '/failures')
        if not os.path.isdir(name):
            os.makedirs(name)
        return name

    def to_string(error, filename=True):
        result = 'crash'
        if (ParserRejects == error):
            result = 'parser_rejects'
        elif (AttributeIgnored == error):
            result = 'attribute_ignored'
        elif (OtherError == error):
            result = 'other_error'
        return result if filename else result.title().replace('_', ' ')

    @trace
    def _process_clang_failure(error, lines, ignored_attributes=set()):
        try:
            (fd, name) = tempfile.mkstemp(suffix=preprocessor_ext(opts.get('language')),
                                          prefix='clang_' + to_string(error),
                                          dir=failure_dir(opts))
            cmds = cmd + ['-E', '-o', name]
            logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
            child = subprocess.Popen(cmds, cwd=cwd)
            child.wait()

            with open(name + '.info.txt', 'w') as ifd:
                ifd.write(os.path.abspath(opts['file']) + os.linesep)
                ifd.write(error_to_string(error, False) + os.linesep)
                ifd.write(' '.join(cmd) + os.linesep)
                ifd.write(subprocess.check_output(['uname', '-a']))
                ifd.write(subprocess.check_output([cmd[0], '-v'], stderr=subprocess.STDOUT))
                ifd.close()

            with open(name + '.stderr.txt', 'w') as efd:
                for line in lines:
                    efd.write(line)
                efd.close()

            for attr in ignored_attributes:
                with open(failure_dir(opts) + 'attribute_ignored_' + attr + '.txt', 'a') as fd:
                    fd.write(os.path.basename(name))
                    fd.close()
        except Exception as ex:
            logging.error('reporting failed: {0}'.format(str(ex)))
            return None
        finally:
            os.close(fd)

    return _process_clang_failure


@trace
def exec_analyzer(cwd, cmd, opts, report_failure):
    def get_output(stream):
        return stream.readlines()

    def copy_to_stderr(lines, fds):
        for line in lines:
            sys.stderr.write(line)

    def report_unhandled_attributes(lines):
        attributes_not_handled = set()
        regexp = re.compile("warning: '([^\']+)' attribute ignored")
        for line in lines:
            match = regexp.match(it.current)
            if match:
                attributes_not_handled.add(match.group(1))
        if attributes_not_handled:
            report_failure(ErrorType.AttributeIgnored, lines, attributes_not_handled)

    try:
        logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
        child = subprocess.Popen(cmd,
                                cwd=cwd,
                                universal_newlines=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        child.wait()
        output = get_output(child.stdout)
        copy_to_stderr(output)
        if 'report_failures' in opts:
            if (child.returncode & 127) and 'html_dir' in opts:
                report_failure(ErrorType.Crash, output)
            elif child.returncode:
                if False:  # FIXME this might be controled by argument
                    report_failure(ErrorType.ParserRejects, output)
                else:
                    report_failure(ErrorType.OtherError, output)
            else:
                report_unhandled_attributes(output)
        return child.returncode
    except Exception as ex:
        logging.error('analyzer failed: {0}'.format(str(ex)))
        return None


@trace
def get_clang_arguments(cwd, clang, mode, args):
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
        cmd = [clang, '-###', mode] + args
        logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
        child = subprocess.Popen(cmd,
                                 cwd=cwd,
                                 universal_newlines=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
        child.wait()
        if 0 == child.returncode:
            return [strip_quotes(x) for x in shlex.split(lastline(child.stdout))]
        else:
            raise Exception(lastline(child.stdout))
    except Exception as e:
        logging.error('exec failed: {0}'.format(str(e)))
        return None


def build_args(opts):
    def regular_parsing():
        result = []
        if 'arch' in opts:
            result.extend(['-arch', opts['arch']])
        if 'compile_options' in opts:
            result.extend(opts['compile_options'])
        result.extend(['-x', opts['language']])
        result.append(opts['file'])
        return result

    def output():
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
            result.append('-analyzer-constraints={0}'.format(opts['constraints_model']))
        if 'internal_stats' in opts:
            result.append('-analyzer-stats')
        if 'analyses' in opts:
            result.extend(opts['analyses'])
        if 'plugins' in opts:
            result.extend(opts['plugins'])
        if 'output_format' in opts:
            result.append('-analyzer-output={0}'.format(opts['output_format']))
        if 'config' in opts:
            result.append(opts['config'])
        # TODO: verbose should add '-analyzer-display-progress'
        # TODO: 'CCC_UBI' should add '-analyzer-viz-egraph-ubigraph'
        return functools.reduce(lambda acc, x: acc + ['-Xclang', x], result, [])

    return (regular_parsing(), (regular_parsing() + output() + static_analyzer()))
