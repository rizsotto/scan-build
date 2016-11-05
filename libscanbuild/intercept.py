# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
""" This module is responsible to capture the compiler invocation of any
build process. The result of that should be a compilation database.

This implementation is using the LD_PRELOAD or DYLD_INSERT_LIBRARIES
mechanisms provided by the dynamic linker. The related library is implemented
in C language and can be found under 'libear' directory.

The 'libear' library is capturing all child process creation and logging the
relevant information about it into separate files in a specified directory.
The parameter of this process is the output directory name, where the report
files shall be placed. This parameter is passed as an environment variable.

The module also implements compiler wrappers to intercept the compiler calls.

The module implements the build command execution and the post-processing of
the output files, which will condensates into a compilation database. """

import sys
import os
import os.path
import re
import itertools
import logging
from libear import build_libear, temporary_directory
from libscanbuild import tempdir, command_entry_point, wrapper_entry_point, \
    wrapper_environment, run_build, run_command, Execution
from libscanbuild.compilation import Compilation, CompilationDatabase
from libscanbuild.arguments import intercept

__all__ = ['capture', 'intercept_build_main', 'intercept_build_wrapper']

GS = chr(0x1d)
RS = chr(0x1e)
US = chr(0x1f)

COMPILER_WRAPPER_CC = 'intercept-cc'
COMPILER_WRAPPER_CXX = 'intercept-c++'
TRACE_FILE_EXTENSION = '.cmd'  # same as in ear.c
WRAPPER_ONLY_PLATFORMS = frozenset({'win32', 'cygwin'})


@command_entry_point
def intercept_build_main():
    """ Entry point for 'intercept-build' command. """

    args = intercept()
    return capture(args)


def capture(args):
    """ Implementation of compilation database generation.

    :param args:    the parsed and validated command line arguments
    :return:        the exit status of build process. """

    with temporary_directory(prefix='intercept-', dir=tempdir()) as tmp_dir:
        # run the build command
        environment = setup_environment(args, tmp_dir)
        exit_code = run_build(args.build, env=environment)
        # To support incremental builds, it is desired to read elements from
        # an existing compilation database from a previous run.
        if 'append' in args and args.append and os.path.isfile(args.cdb):
            previous = CompilationDatabase.load(args.cdb)
        else:
            previous = iter([])
        # read the intercepted exec calls
        exec_calls = exec_calls_from(exec_trace_files(tmp_dir))
        current = compilations(exec_calls, args.cc, args.cxx)
        # merge compilation from previous and current run
        entries = iter(set(itertools.chain(previous, current)))
        # and dump the unique elements into the output file
        CompilationDatabase.save(args.cdb, entries)
        return exit_code


def compilations(exec_calls, cc, cxx):
    """ Needs to filter out commands which are not compiler calls. And those
    compiler calls shall be compilation (not pre-processing or linking) calls.
    Plus needs to find the source file name from the arguments.

    :param exec_calls:  iterator of executions
    :param cc:          user specified C compiler name
    :param cxx:         user specified C++ compiler name
    :return: stream of formatted compilation database entries """

    for call in exec_calls:
        for entry in Compilation.from_call(call, cc, cxx):
            yield entry


def setup_environment(args, destination):
    """ Sets up the environment for the build command.

    In order to capture the sub-commands (executed by the build process),
    it needs to prepare the environment. It's either the compiler wrappers
    shall be announce as compiler or the intercepting library shall be
    announced for the dynamic linker.

    :param args:        command line arguments
    :param destination: directory path for the execution trace files
    :return: a prepared set of environment variables. """

    use_wrapper = args.override_compiler or is_preload_disabled(sys.platform)

    environment = dict(os.environ)
    environment.update({'INTERCEPT_BUILD_TARGET_DIR': destination})

    if use_wrapper:
        environment.update(wrapper_environment(args))
        environment.update({
            'CC': COMPILER_WRAPPER_CC,
            'CXX': COMPILER_WRAPPER_CXX,
        })
    else:
        intercept_library = build_libear(args.cc, destination)
        if sys.platform == 'darwin':
            environment.update({
                'DYLD_INSERT_LIBRARIES': intercept_library,
                'DYLD_FORCE_FLAT_NAMESPACE': '1'
            })
        else:
            environment.update({'LD_PRELOAD': intercept_library})

    return environment


@command_entry_point
@wrapper_entry_point
def intercept_build_wrapper(**kwargs):
    """ Entry point for `intercept-cc` and `intercept-c++` compiler wrappers.

    It does generate execution report into target directory.
    The target directory name is from environment variables. """

    message_prefix = 'execution report might be incomplete: %s'

    target_dir = os.getenv('INTERCEPT_BUILD_TARGET_DIR')
    if not target_dir:
        logging.warning(message_prefix, 'missing target directory')
        return
    # append the current execution info to the pid file
    try:
        target_file_name = str(os.getpid()) + TRACE_FILE_EXTENSION
        target_file = os.path.join(target_dir, target_file_name)
        logging.debug('writing execution report to: %s', target_file)
        write_exec_trace(target_file, kwargs['execution'])
    except IOError:
        logging.warning(message_prefix, 'io problem')


def write_exec_trace(filename, entry):
    """ Write execution report file.

    This method shall be sync with the execution report writer in interception
    library. The file format is very simple and easy to implement in both
    programming language (C and python). The main focus of the format to be
    human readable and easy to reconstruct the different types from it.

    Integers are converted to string. String lists are concatenated with
    special characters. Fields are separated with special characters. (Field
    names are not given, the position identifies the field.)

    :param filename:    path to the output execution trace file,
    :param entry:       the Execution object to append to that file. """

    # create the payload first
    command = US.join(entry.command) + US
    pid = str(entry.pid)
    ppid = str(entry.ppid)
    content = RS.join([pid, ppid, entry.function, entry.directory, command
                       ]) + GS
    # write it into the target file
    with open(filename, 'ab') as handler:
        # FIXME why convert it to string?
        handler.write(content.encode('utf-8'))


def parse_exec_trace(filename):
    """ Parse execution report file.

    Given filename points to a file which contains the basic report
    generated by the interception library or compiler wrapper. A single
    report file _might_ contain multiple process creation info.

    :param filename: path to an execution trace file to read from,
    :return: stream of Execution objects. """

    logging.debug(filename)
    with open(filename, 'r') as handler:
        content = handler.read()
        for group in filter(bool, content.split(GS)):
            records = group.split(RS)
            yield Execution(
                pid=int(records[0]),
                ppid=int(records[1]),
                function=records[2],
                directory=records[3],
                command=records[4].split(US)[:-1])


def exec_trace_files(directory):
    """ Generates exec trace file names.

    :param directory:   path to directory which contains the trace files.
    :return:            a generator of file names (absolute path). """

    for root, _, files in os.walk(directory):
        for candidate in files:
            __, extension = os.path.splitext(candidate)
            if extension == TRACE_FILE_EXTENSION:
                yield os.path.join(root, candidate)


def exec_calls_from(trace_files):
    """ Generator of execution objects from execution trace files.

    :param trace_files: iterator of file names which can contains exec trace
    :return:            a generator of parsed exec traces. """

    for trace_file in trace_files:
        for exec_call in parse_exec_trace(trace_file):
            yield exec_call


def is_preload_disabled(platform):
    """ Library-based interposition will fail silently if SIP is enabled,
    so this should be detected. You can detect whether SIP is enabled on
    Darwin by checking whether (1) there is a binary called 'csrutil' in
    the path and, if so, (2) whether the output of executing 'csrutil status'
    contains 'System Integrity Protection status: enabled'.

    :param platform: name of the platform (returned by sys.platform),
    :return: True if library preload will fail by the dynamic linker. """

    if platform in WRAPPER_ONLY_PLATFORMS:
        return True
    elif platform == 'darwin':
        command = ['csrutil', 'status']
        pattern = re.compile(r'System Integrity Protection status:\s+enabled')
        try:
            return any(pattern.match(line) for line in run_command(command))
        except:
            return False
    else:
        return False
