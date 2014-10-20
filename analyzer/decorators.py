# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import functools


TRACE_LEVEL = 5


def _trace(message):
    logging.log(TRACE_LEVEL, message)


def _name(function):
    return function.__qualname__\
        if dir(function).count('__qualname__') else function.__name__


TRACE_METHOD = _trace


def to_logging_level(num):
    """ Convert the count of verbose flags to logging level. """
    if 0 == num:
        return logging.WARNING
    elif 1 == num:
        return logging.INFO
    elif 2 == num:
        return logging.DEBUG
    else:
        return TRACE_LEVEL


def trace(function):
    """ Decorator to simplify debugging. """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            TRACE_METHOD('entering {0}'.format(_name(function)))
            return function(*args, **kwargs)
        except:
            TRACE_METHOD('exception in {0}'.format(_name(function)))
            raise
        finally:
            TRACE_METHOD('leaving {0}'.format(_name(function)))

    return wrapper


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


def entry(function):
    """ Decorator for program entry points. """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        from multiprocessing import freeze_support
        freeze_support()

        from sys import argv
        from os.path import basename
        program = basename(argv[0])
        logging.basicConfig(format='{0}: %(message)s'.format(program))

        try:
            return function(*args, **kwargs)
        except KeyboardInterrupt:
            return 1
        except Exception as exception:
            logging.error(str(exception))
            return 127

    return wrapper
