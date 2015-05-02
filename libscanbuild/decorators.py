# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import functools

__all__ = ['require']


def _name(function):
    return function.__qualname__\
        if dir(function).count('__qualname__') else function.__name__


def require(required):
    """ Decorator for checking the required values in state.

    It checks the required attributes in the passed state and stop when
    any of those is missing.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            for key in required:
                if key not in args[0]:
                    raise KeyError(
                        '{0} not passed to {1}'.format(key, _name(function)))

            return function(*args, **kwargs)

        return wrapper

    return decorator
