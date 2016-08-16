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

WRAPPER_CC = 'INTERCEPT_BUILD_CC'
WRAPPER_CXX = 'INTERCEPT_BUILD_CXX'
WRAPPER_VERBOSE = 'INTERCEPT_BUILD_VERBOSE'


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


def run_build(build_command, environment):
    """ Run and report build command execution """

    logging.debug('run build in environment: %s', environment)
    exit_code = subprocess.call(build_command, env=environment)
    logging.debug('build finished with exit code: %d', exit_code)
    return exit_code


def reconfigure_logging(verbose_level):
    """ Logging level and format reconfigured based on the verbose flag. """

    # exit when nothing to do
    if verbose_level == 0:
        return

    root = logging.getLogger()
    # tune level
    level = logging.WARNING - min(logging.WARNING, (10 * verbose_level))
    root.setLevel(level)
    # be verbose with messages
    if verbose_level <= 3:
        fmt_string = '%(name)s: %(levelname)s: %(message)s'
    else:
        fmt_string = '%(name)s: %(levelname)s: %(funcName)s: %(message)s'
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt=fmt_string))
    root.handlers = [handler]


def command_entry_point(function):
    """ Decorator for command entry methods.

    The decorator initialize/shutdown logging and guard on programming
    errors (catch exceptions).

    The decorated method can have arbitrary parameters, the return value will
    be the exit code of the process. """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        """ Do housekeeping tasks and execute the wrapped method. """

        exit_code = 127
        try:
            logging.basicConfig(format='%(name)s: %(message)s',
                                level=logging.WARNING)
            logging.getLogger().name = os.path.basename(sys.argv[0])
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
                              "verbose mode (add '-vvvv' as argument).")
        finally:
            logging.shutdown()
            return exit_code

    return wrapper


def wrapper_entry_point(function):
    """ Decorator for wrapper command entry methods.

    The decorator itself execute the real compiler call. Then it calls the
    decorated method. The method will receive dictionary of parameters.

    - compiler:     the compiler name which was executed.
    - command:      the command executed by the wrapper.
    - result:       the exit code of the compilation.

    The return value will be the exit code of the compiler call. (The
    decorated method return value is ignored.)

    If the decorated method throws exception, it will be caught and logged. """

    @functools.wraps(function)
    def wrapper():
        """ It executes the compilation and calls the wrapped method. """

        # set logging level when neeeded
        verbose = bool(os.getenv(WRAPPER_VERBOSE, '0'))
        reconfigure_logging(verbose)
        # find out what is the real compiler
        is_cxx = os.path.basename(sys.argv[0]).endswith('++')
        compiler = os.getenv(WRAPPER_CXX) if is_cxx else os.getenv(WRAPPER_CC)
        # execute compilation with the real compiler
        command = [compiler] + sys.argv[1:]
        logging.debug('compilation: %s', command)
        result = subprocess.call(command)
        logging.debug('compilation exit code: %d', result)
        # call the wrapped method and ignore it's return value ...
        try:
            function(compiler=compiler, command=command, result=result)
        except:
            logging.exception('Compiler wrapper failed complete.')
        # ... return the real compiler exit code instead.
        return result

    return wrapper


def wrapper_environment(c_wrapper, cxx_wrapper, c_compiler, cxx_compiler,
                        verbose):
    """ Set up environment for build command to interpose compiler wrapper. """

    return {
        'CC': c_wrapper,
        'CXX': cxx_wrapper,
        WRAPPER_CC: c_compiler,
        WRAPPER_CXX: cxx_compiler,
        WRAPPER_VERBOSE: str(verbose)
    }
