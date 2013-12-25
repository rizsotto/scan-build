# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import subprocess
import logging
import six
import re
import os
import os.path
import tempfile
import copy


class Action:
    Link, Compile, Preprocess, Info = range(4)


def parse(args):
    def match(state, it):
        def regex(pattern, action):
            regexp = re.compile(pattern)

            def eval(it):
                match = regexp.match(it.current)
                if match is not None:
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
            if '' == match.group(1):
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

    state = {
        'action': Action.Link
    }
    try:
        it = ArgumentIterator(args[1:])
        while True:
            it.next()
            match(state, it)
    except StopIteration:
        return state
    except Exception:
        logging.exception('parsing failed')


def language_from_filename(fn):
    mapping = {
      '.c'   : 'c',
      '.cp'  : 'c++',
      '.cpp' : 'c++',
      '.cxx' : 'c++',
      '.txx' : 'c++',
      '.cc'  : 'c++',
      '.C'   : 'c++',
      '.ii'  : 'c++',
      '.i'   : 'c-cpp-output',
      '.m'   : 'objective-c',
      '.mi'  : 'objective-c-cpp-output',
      '.mm'  : 'objective-c++'
    }
    (_, extension) = os.path.splitext(os.path.basename(fn))
    return mapping.get(extension)


def filter_dict(original, removables, additions):
    new = copy.deepcopy(original)
    for k in removables:
        if k in new:
            new.pop(k)
    for (k, v) in additions.items():
        new[k] = v
    return new


def arch_loop(opts, continuation):
    disableds = ['ppc', 'ppc64']

    key = 'archs_seen'
    if key in opts:
        archs = set([a for a in d[key] if '-arch' != a and a not in disableds])
        if archs:
            for arch in archs:
                logging.debug('  analysis, on arch: {0}'.format(arch))
                continuation(filter_dict(opts, [key], {'arch': arch}))
        else:
            logging.debug('skip analysis, found not supported arch')
    else:
        logging.debug('  analysis, on default arch')
        continuation(opts)


def files_loop(opts, continuation):
    if 'files' in opts:
        for fn in opts['files']:
            logging.debug('  analysis, source file: {0}'.format(fn))
            continuation(filter_dict(opts, ['files'], {'file': fn}))
    else:
        logging.debug('skip analysis, source file not found')


def set_language(opts, continuation):
    accepteds = ['c', 'c++', 'objective-c', 'objective-c++']

    fn = opts['file']
    language = opts.get('language', language_from_filename(fn))
    if language is None:
        logging.debug('skip analysis, language not known')
    elif language not in accepteds:
        logging.debug('skip analysis, language not supported')
    else:
        logging.debug('  analysis, language: {0}'.format(language))
        continuation(filter_dict(opts, [], {'language': language}))


def set_analyzer_output(opts, continuation):
    if 'output_format' in opts:
        output_format = opts['output_format']
        if re.match('plist', output_format):
            html_dir = opts.get('html_dir')
            (h, analyzer_output) = tempfile.mkstemp(suffix='.plist',
                                                    prefix='report-',
                                                    dir=html_dir)
            os.close(h)
            logging.debug('analyzer output: {0}'.format(analyzer_output))
            continuation(filter_dict(opts, [], {'analyzer_output': analyzer_output}))
            if html_dir is None:
                try:
                    os.remove(analyzer_output)
                except:
                    logging.warning('cleanup analyzer output file failed {0}'.format(analyzer_output))
        else:
            continuation(opts)
    else:
        continuation(opts)


def run(**kwargs):
    def stack(conts):
        def bind(cs, acc):
            return bind(cs[1:], lambda x: cs[0](x, acc)) if cs else acc

        conts.reverse()
        return bind(conts, lambda x: logging.debug('  end of analysis chain'))

    opts = parse(kwargs['command'].split())
    # move it to a separate step and make it conditional
    os.chdir(kwargs['directory'])

    stack([arch_loop, files_loop, set_language, set_analyzer_output])(opts)


class Analyzer:
    def run(self, **kwargs):
        os.chdir(kwargs['directory'])
        os.environ['CCC_ANALYZER_HTML'] = kwargs.get('html_dir')
        cmds = kwargs['command'].split()
        cmds[0] = '/usr/lib/clang-analyzer/scan-build/ccc-analyzer'
        logging.debug('executing: {0}'.format(cmds))
        analyze = subprocess.Popen(cmds, env=os.environ)
        analyze.wait()
        return analyze.returncode
