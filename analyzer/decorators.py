# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import functools


def trace(function):
    """ Decorator to simplify debugging. """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        name = function.__qualname__\
            if dir(function).count('__qualname__') else function.__name__
        logging.log(5, 'entering {0}'.format(name))
        result = function(*args, **kwargs)
        logging.log(5, 'leaving {0}'.format(name))
        return result

    return wrapper


def require(required=[]):
    """ Decorator for checking the required values in state.

    It checks the required attributes in the passed state and stop when
    any of those is missing.
    """
    def decorator(function):
        @functools.wraps(function)
        def wrapper(opts, *rest):
            try:
                precondition(opts)
                return function(opts, *rest)
            except Exception as e:
                logging.error(str(e))
                return {'error': {'exception': e,
                                  'function': function.__name__},
                        'input': opts}

        def precondition(opts):
            for key in required:
                if key not in opts:
                    raise KeyError(
                        '{0} not passed to {1}'.format(key, function.__name__))

        return wrapper

    return decorator
