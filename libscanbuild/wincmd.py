# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
""" This module implements basic cmd escaping/unescaping methods. """

import shlex

__all__ = ['encode', 'decode']


def encode(command):
    """ Takes a command as list and returns a string. """

    return " ".join([arg for arg in command])


def decode(string):
    """ Takes a command string and returns as a list. """

    return string.split()
