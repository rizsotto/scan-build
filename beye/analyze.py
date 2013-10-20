# -*- coding: utf-8 -*-

# Copyright 2013 by László Nagy
# This file is part of Beye [see file LICENSE.txt for more]

import subprocess
import logging
import six
import re


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
    def match(state, it):
        task_map = [
            #
            (re.compile('^-(E|MM?)$'), take_action(Action.Preprocess)),
            (re.compile('^-c$'), take_action(Action.Compile)),
            (re.compile('^-print-prog-name$'), take_action(Action.Info)),
            #
            (re.compile('^-arch$'), take_two('archs_seen', 'compile_options', 'link_options')),
            #
            (re.compile('^-filelist$'), take_from_file('files')),
            (re.compile('^[^-].+'), take_one('files')),
            #
            (re.compile('^-x$'), take_second('language')),
            #
            (re.compile('^-o$'), take_second('output')),
            #
            (re.compile('^-write-strings$'), take_one('compile_options', 'link_options')),
            (re.compile('^-ftrapv-handler$'), take_two('compile_options', 'link_options')),
            (re.compile('^-mios-simulator-version-min(.*)'), take_joined('compile_options', 'link_options')),
            (re.compile('^-isysroot'), take_two('compile_options', 'link_options')),
            (re.compile('^-m(32|64)$'), take_one('compile_options', 'link_options')),
            (re.compile('^-stdlib(.*)'), take_joined('compile_options', 'link_options')),
            (re.compile('^-target$'), take_two('compile_options', 'link_options')),
            (re.compile('^-v$'), take_one('compile_options', 'link_options')),
            (re.compile('^-mmacosx-version-min(.*)'), take_joined('compile_options', 'link_options')),
            (re.compile('^-miphoneos-version-min(.*)'), take_joined('compile_options', 'link_options')),
            (re.compile('^-O[1-3]$'), take_one('compile_options', 'link_options')),
            (re.compile('^-O$'), take_as('-O1', 'compile_options', 'link_options')),
            (re.compile('^-Os$'), take_as('-O2', 'compile_options', 'link_options')),
            #
            (re.compile('^-[DIU](.*)$'), take_joined('compile_options')),
            (re.compile('^-nostdinc$'), take_one('compile_options')),
            (re.compile('^-std='), take_one('compile_options')),
            (re.compile('^-include'), take_two('compile_options')),
            (re.compile('^-idirafter$'), take_two('compile_options')),
            (re.compile('^-imacros$'), take_two('compile_options')),
            (re.compile('^-iprefix$'), take_two('compile_options')),
            (re.compile('^-isystem$'), take_two('compile_options')),
            (re.compile('^-iwithprefix(before)?$'), take_two('compile_options')),
            (re.compile('^-m.*'), take_one('compile_options')),
            (re.compile('^-iquote(.*)'), take_joined('compile_options')),
            (re.compile('^-Wno-'), take_one('compile_options')),
            #
            (re.compile('^-framework$'), take_two('link_options')),
            (re.compile('^-fobjc-link-runtime(.*)'), take_joined('link_options')),
            (re.compile('^-[lL]'), take_one('link_options')),
            # ignore
            (re.compile('^-M[TF]$'), take_two()),
            (re.compile('^-fsyntax-only$'), take_one()),
            (re.compile('^-save-temps$'), take_one()),
            (re.compile('^-install_name$'), take_two()),
            (re.compile('^-exported_symbols_list$'), take_two()),
            (re.compile('^-current_version$'), take_two()),
            (re.compile('^-compatibility_version$'), take_two()),
            (re.compile('^-init$'), take_two()),
            (re.compile('^-[eu]$'), take_two()),
            (re.compile('^-seg1addr$'), take_two()),
            (re.compile('^-bundle_loader$'), take_two()),
            (re.compile('^-multiply_defined$'), take_two()),
            (re.compile('^-sectorder$'), take_four()),
            (re.compile('^--param$'), take_two()),
            (re.compile('^--serialize-diagnostics$'), take_two()),
            #
            (re.compile('^-[fF](.+)$'), take_one('compile_options', 'link_options'))
        ]
        for pattern, task in task_map:
            match = pattern.match(it.current)
            if match is not None:
                task(state, it, match)
                return

    def extend(values, key, value):
        if key in values:
            values.get(key).extend(value)
        else:
            values[key] = value

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
        def take(values, it, match):
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

    def fix_seen_archs(d):
        key = 'archs_seen'
        if key in d:
            filtered = {v for v in d[key] if not '-arch' == v}
            d[key] = filtered
        else:
            d[key] = set()

    state = {
        'action': Action.Link
    }
    try:
        it = Iterator(args[1:])
        while True:
            it.next()
            match(state, it)
    except StopIteration:
        fix_seen_archs(state)
        return state
    except Exception:
        logging.exception('parsing failed')


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
