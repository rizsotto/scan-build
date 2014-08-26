# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import functools


__all__ = ['trace', 'require']


def _trace(message):
    logging.log(5, message)


def _name(function):
    return function.__qualname__\
        if dir(function).count('__qualname__') else function.__name__


trace_method = _trace


def trace(function):
    """ Decorator to simplify debugging. """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            trace_method('entering {0}'.format(_name(function)))
            return function(*args, **kwargs)
        except:
            trace_method('exception in {0}'.format(_name(function)))
            raise
        finally:
            trace_method('leaving {0}'.format(_name(function)))

    return wrapper


def require(required):
    """ Decorator for checking the required values in state.

    It checks the required attributes in the passed state and stop when
    any of those is missing.
    """
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            try:
                precondition(args[0])
                return function(*args, **kwargs)
            except Exception as exception:
                logging.error(str(exception))
                return {'error': {'exception': exception,
                                  'function': function.__name__},
                        'input': opts}

        def precondition(opts):
            for key in required:
                if key not in opts:
                    raise KeyError(
                        '{0} not passed to {1}'.format(key, function.__name__))

        return wrapper

    return decorator
