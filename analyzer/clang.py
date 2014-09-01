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
def get_default_checkers(clang):
    """ To get the default plugins we execute Clang to print how this
    comilation would be called. For input file we specify stdin. And
    pass only language information. """
    def checkers(language):
        pattern = re.compile(r'^-analyzer-checker=(.*)$')
        cmd = [clang, '--analyze', '-x', language, '-']
        return [pattern.match(arg).group(1)
                for arg in get_arguments('.', cmd) if pattern.match(arg)]

    return set(
        itertools.chain.from_iterable(
            [checkers(language)
             for language
             in ['c', 'c++', 'objective-c', 'objective-c++']]))
