# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import subprocess
import logging
import re
import shlex
import itertools
import functools
from analyzer.decorators import trace


@trace
def get_version(cmd):
    """ Returns the compiler version as string. """
    lines = subprocess.check_output([cmd, '-v'], stderr=subprocess.STDOUT)
    return lines.decode('ascii').splitlines()[0]


@trace
def get_arguments(cwd, command):
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
        match = re.match(r'^\"([^\"]*)\"$', quoted)
        return match.group(1) if match else quoted

    cmd = command[:]
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
        if re.match(r'^clang: error:', line):
            raise Exception(line)
        return [strip_quotes(x) for x in shlex.split(line)]
    else:
        raise Exception(line)


@trace
def _get_active_checkers(clang, plugins):
    """ To get the default plugins we execute Clang to print how this
    comilation would be called. For input file we specify stdin. And
    pass only language information. """
    def checkers(language, load):
        pattern = re.compile(r'^-analyzer-checker=(.*)$')
        cmd = [clang, '--analyze'] + load + ['-x', language, '-']
        return [pattern.match(arg).group(1)
                for arg in get_arguments('.', cmd) if pattern.match(arg)]

    load = functools.reduce(
        lambda acc, x: acc + ['-Xclang', '-load', '-Xclang', x],
        plugins if plugins else [],
        [])

    return set(
        itertools.chain.from_iterable(
            [checkers(language, load)
             for language
             in ['c', 'c++', 'objective-c', 'objective-c++']]))


@trace
def get_checkers(clang, plugins):
    def parse_checkers(stream):
        # find checkers header
        for line in stream:
            if re.match(r'^CHECKERS:', line):
                break
        # find entries
        result = {}
        state = None
        for line in stream:
            if state and not re.match(r'^\s\s\S', line):
                result.update({state: line.strip()})
                state = None
            elif re.match(r'^\s\s\S+$', line.rstrip()):
                state = line.strip()
            else:
                pattern = re.compile(r'^\s\s(?P<key>\S*)\s*(?P<value>.*)')
                match = pattern.match(line.rstrip())
                if match:
                    current = match.groupdict()
                    result.update({current['key']: current['value']})
        return result

    def is_active(entry, actives):
        for active in actives:
            if re.match('^' + active + '(\.|$)', entry):
                return True
        return False

    load = functools.reduce(
        lambda acc, x: acc + ['-load', x],
        plugins if plugins else [],
        [])

    cmd = [clang, '-cc1'] + load + ['-analyzer-checker-help']
    logging.debug('exec command: {0}'.format(' '.join(cmd)))
    child = subprocess.Popen(cmd,
                             universal_newlines=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    checkers = parse_checkers(child.stdout)
    child.wait()
    if 0 == child.returncode and len(checkers):
        actives = _get_active_checkers(clang, plugins)
        return {k: (v, is_active(k, actives)) for k, v in checkers.items()}
    else:
        raise Exception('Could not query Clang for available checkers.')
