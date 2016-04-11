# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
""" This module is a collection of methods commonly used in this project. """

import os
import os.path
import sys
import logging
import functools
import subprocess


def duplicate_check(method):
    """ Predicate to detect duplicated entries.

    Unique hash method can be use to detect duplicates. Entries are
    represented as dictionaries, which has no default hash method.
    This implementation uses a set datatype to store the unique hash values.

    This method returns a method which can detect the duplicate values. """

    def predicate(entry):
        entry_hash = predicate.unique(entry)
        if entry_hash not in predicate.state:
            predicate.state.add(entry_hash)
            return False
        return True

    predicate.unique = method
    predicate.state = set()
    return predicate


def tempdir():
    """ Return the default temorary directory. """

    return os.getenv('TMPDIR', os.getenv('TEMP', os.getenv('TMP', '/tmp')))


def initialize_logging(verbose_level):
    """ Output content controlled by the verbosity level. """

    level = logging.WARNING - min(logging.WARNING, (10 * verbose_level))

    if verbose_level <= 3:
        fmt_string = '{0}: %(levelname)s: %(message)s'
    else:
        fmt_string = '{0}: %(levelname)s: %(funcName)s: %(message)s'

    program = os.path.basename(sys.argv[0])
    logging.basicConfig(format=fmt_string.format(program), level=level)


def command_entry_point(function):
    """ Decorator for command entry methods. """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):

        exit_code = 127
        try:
            exit_code = function(*args, **kwargs)
        except KeyboardInterrupt:
            logging.warning('Keyboard interupt')
        except Exception:
            logging.exception('Internal error.')
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.error("Please report this bug and attach the output "
                              "to the bug report")
            else:
                logging.error("Please run this command again and turn on "
                              "verbose mode (add '-vvv' as argument).")
        finally:
            return exit_code

    return wrapper


def wrapper_entry_point(function):
    """ Decorator for wrapper command entry methods.

    The decorator itself execute the real compiler call. Then it calls the
    decorated method. The method will receive dictionary of parameters.

    - compiler:     the compiler name which was executed.
    - compilation:  the command executed by the wrapper.
    - result:       the exit code of the compilation.

    The return value will be the exit code of the compiler call. (The
    decorated method return value is ignored.)

    If the decorated method throws exception, it will be caught and logged. """

    @functools.wraps(function)
    def wrapper():
        """ It executes the compilation and calls the wrapped method. """

        # initialize wrapper logging
        wrapper_name = os.path.basename(sys.argv[0])
        logging.basicConfig(format='{0}: %(message)s'.format(wrapper_name),
                            level=os.getenv('INTERCEPT_BUILD_VERBOSE', 'INFO'))
        # execute with real compiler
        language = 'c++' if wrapper_name[-2:] == '++' else 'c'
        compiler = os.getenv('INTERCEPT_BUILD_CC', 'cc') if language == 'c' \
            else os.getenv('INTERCEPT_BUILD_CXX', 'c++')
        compilation = [compiler] + sys.argv[1:]
        logging.debug('compilation: %s', compilation)
        result = subprocess.call(compilation)
        logging.debug('compilation exit code: %d', result)
        # call the wrapped method and ignore it's return value ...
        try:
            function(compiler=compiler, command=compilation, result=result)
        except:
            logging.warning('wrapped function failed')
        finally:
            logging.shutdown()
        # ... return the real compiler exit code instead.
        return result

    return wrapper
