#!/usr/bin/env python
# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import os
import re
import sys
import random


def comment(line):
    return re.match(r'^(#|//).*', line)


def random_filename():
    def random_char():
        return random.choice([chr(random.randrange(ord('a'), ord('z'), 1)),
                              chr(random.randrange(ord('A'), ord('Z'), 1))])

    return ''.join(random_char() for _ in range(12))


def substitute(line):

    def lookup(key):
        return random_filename() if key == 'random' else os.environ[key]

    requests = re.findall(r'\$\{([^\}]+)\}', line)
    if requests:
        replace = {re.escape(request): lookup(request) for request in requests}
        for key, value in replace.items():
            line = re.sub(r'\$\{' + key + r'\}', value, line)
    return line


def main():
    """ Substitute environment literals in a given compilation database. """
    inputs = (line for line in sys.stdin)
    outputs = (substitute(line) for line in inputs if not comment(line))
    for line in outputs:
        sys.stdout.write(line)
    return 0
