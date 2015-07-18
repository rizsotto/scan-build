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

The module implements the build command execution with the 'libear' library
and the post-processing of the output files, which will condensates into a
(might be empty) compilation database. """

import logging
import subprocess
import json
import sys
import os
import os.path
import re
import shlex
import glob
import itertools
from libear import ear_library
from libscanbuild import duplicate_check, tempdir
from libscanbuild.command import Action, classify_parameters

__all__ = ['capture', 'wrapper']

GS = chr(0x1d)
RS = chr(0x1e)
US = chr(0x1f)


def capture(args, wrappers_dir):
    """ The entry point of build command interception. """

    def post_processing(commands):
        # run post processing only if that was requested
        if 'raw_entries' not in args or not args.raw_entries:
            # create entries from the current run
            current = itertools.chain.from_iterable(
                # creates a sequence of entry generators from an exec,
                # but filter out non compiler calls before.
                (format_entry(x) for x in commands if is_compiler_call(x)))
            # read entries from previous run
            if 'append' in args and args.append and os.path.exists(args.cdb):
                with open(args.cdb) as handle:
                    previous = iter(json.load(handle))
            else:
                previous = iter([])
            # filter out duplicate entries from both
            duplicate = duplicate_check(entry_hash)
            return (entry for entry in itertools.chain(previous, current)
                    if os.path.exists(entry['file']) and not duplicate(entry))
        return commands

    with TemporaryDirectory(prefix='build-intercept', dir=tempdir()) as tmpdir:
        # run the build command
        environment = setup_environment(args, tmpdir, wrappers_dir)
        logging.debug('run build in environment: %s', environment)
        exit_code = subprocess.call(args.build, env=environment)
        logging.debug('build finished with exit code: %d', exit_code)
        # read the intercepted exec calls
        commands = (parse_exec_trace(os.path.join(tmpdir, filename))
                    for filename
                    in sorted(glob.iglob(os.path.join(tmpdir, '*.cmd'))))
        # do post processing
        entries = post_processing(itertools.chain.from_iterable(commands))
        # dump the compilation database
        with open(args.cdb, 'w+') as handle:
            json.dump(list(entries), handle, sort_keys=True, indent=4)
        return exit_code


def setup_environment(args, destination, wrappers_dir):
    """ Sets up the environment for the build command.

    It sets the required environment variables and execute the given command.
    The exec calls will be logged by the 'libear' preloaded library or by the
    'wrapper' programs. """

    compiler = args.cc if 'cc' in args.__dict__ else 'cc'
    ear_library_path = ear_library(compiler, destination)

    environment = dict(os.environ)
    environment.update({'BUILD_INTERCEPT_TARGET_DIR': destination})

    if sys.platform in {'win32', 'cygwin'} or not ear_library_path:
        environment.update({
            'CC': os.path.join(wrappers_dir, 'intercept-cc'),
            'CXX': os.path.join(wrappers_dir, 'intercept-cxx'),
            'BUILD_INTERCEPT_CC': args.cc,
            'BUILD_INTERCEPT_CXX': args.cxx,
            'BUILD_INTERCEPT_VERBOSE': 'DEBUG' if args.verbose > 2 else 'INFO'
        })
    elif 'darwin' == sys.platform:
        environment.update({
            'DYLD_INSERT_LIBRARIES': ear_library_path,
            'DYLD_FORCE_FLAT_NAMESPACE': '1'
        })
    else:
        environment.update({'LD_PRELOAD': ear_library_path})

    return environment


def wrapper(cplusplus):
    """ This method implements basic compiler wrapper functionality.

    It does generate execution report into target directory. And execute
    the wrapped compilation with the real compiler. The parameters for
    report and execution are from environment variables.

    Those parameters which for 'libear' library can't have meaningful
    values are faked. """

    # initialize wrapper logging
    logging.basicConfig(format='intercept: %(levelname)s: %(message)s',
                        level=os.getenv('BUILD_INTERCEPT_VERBOSE', 'INFO'))
    # write report
    try:
        target_dir = os.getenv('BUILD_INTERCEPT_TARGET_DIR')
        if not target_dir:
            raise UserWarning('exec report target directory not found')
        pid = str(os.getpid())
        target_file = os.path.join(target_dir, pid + '.cmd')
        logging.debug('writing exec report to: %s', target_file)
        with open(target_file, 'ab') as handler:
            working_dir = os.getcwd()
            command = US.join(sys.argv) + US
            content = RS.join([pid, pid, 'wrapper', working_dir, command]) + GS
            handler.write(content.encode('utf-8'))
    except IOError:
        logging.exception('writing exec report failed')
    except UserWarning as warning:
        logging.warning(warning)
    # execute with real compiler
    compiler = os.getenv('BUILD_INTERCEPT_CXX', 'c++') if cplusplus \
        else os.getenv('BUILD_INTERCEPT_CC', 'cc')
    compilation = [compiler] + sys.argv[1:]
    logging.debug('execute compiler: %s', compilation)
    return subprocess.call(compilation)


def parse_exec_trace(filename):
    """ Parse the file generated by the 'libear' preloaded library.

    Given filename points to a file which contains the basic report
    generated by the interception library or wrapper command. A single
    report file _might_ contain multiple process creation info. """

    with open(filename, 'r') as handler:
        content = handler.read()
        for group in filter(bool, content.split(GS)):
            records = group.split(RS)
            yield {
                'pid': records[0],
                'ppid': records[1],
                'function': records[2],
                'directory': records[3],
                'command': records[4].split(US)[:-1]
            }


def format_entry(entry):
    """ Generate the desired fields for compilation database entries. """

    def join_command(args):
        return ' '.join([shell_escape(arg) for arg in args])

    def abspath(cwd, name):
        """ Create normalized absolute path from input filename. """
        fullname = name if os.path.isabs(name) else os.path.join(cwd, name)
        return os.path.normpath(fullname)

    atoms = classify_parameters(entry['command'])
    return ({
        'directory': entry['directory'],
        'command': join_command(entry['command']),
        'file': abspath(entry['directory'], filename)
    } for filename in atoms.get('files', [])
            if is_source_file(filename) and atoms['action'] <= Action.Compile)


def shell_escape(arg):
    """ Create a single string from list.

    The major challenge, to deal with white spaces. Which are used by
    the shell as separator. (Eg.: -D_KEY="Value with spaces") """

    def quote(arg):
        table = {'\\': '\\\\', '"': '\\"', "'": "\\'"}
        return '"' + ''.join([table.get(c, c) for c in arg]) + '"'

    return quote(arg) if len(shlex.split(arg)) > 1 else arg


def is_source_file(filename):
    """ A predicate to decide the filename is a source file or not. """

    accepted = {
        '.c', '.C', '.cc', '.CC', '.cxx', '.cp', '.cpp', '.c++', '.m', '.mm',
        '.i', '.ii', '.mii'
    }
    _, ext = os.path.splitext(filename)
    return ext in accepted


def is_compiler_call(entry):
    """ A predicate to decide the entry is a compiler call or not. """

    patterns = [
        re.compile(r'^([^/]*/)*intercept-c(c|\+\+)$'),
        re.compile(r'^([^/]*/)*c(c|\+\+)$'),
        re.compile(r'^([^/]*/)*([^-]*-)*g(cc|\+\+)(-\d+(\.\d+){0,2})?$'),
        re.compile(r'^([^/]*/)*([^-]*-)*clang(\+\+)?(-\d+(\.\d+){0,2})?$'),
        re.compile(r'^([^/]*/)*llvm-g(cc|\+\+)$'),
    ]
    executable = entry['command'][0]
    return any((pattern.match(executable) for pattern in patterns))


def entry_hash(entry):
    """ Implement unique hash method for compilation database entries. """

    # For faster lookup in set filename is reverted
    filename = entry['file'][::-1]
    # For faster lookup in set directory is reverted
    directory = entry['directory'][::-1]
    # On OS X the 'cc' and 'c++' compilers are wrappers for
    # 'clang' therefore both call would be logged. To avoid
    # this the hash does not contain the first word of the
    # command.
    command = ' '.join(shlex.split(entry['command'])[1:])

    return '<>'.join([filename, directory, command])


if sys.version_info.major >= 3 and sys.version_info.minor >= 2:
    from tempfile import TemporaryDirectory
else:

    class TemporaryDirectory(object):
        """ This function creates a temporary directory using mkdtemp() (the
        supplied arguments are passed directly to the underlying function).
        The resulting object can be used as a context manager. On completion
        of the context or destruction of the temporary directory object the
        newly created temporary directory and all its contents are removed
        from the filesystem. """

        def __init__(self, **kwargs):
            from tempfile import mkdtemp
            self.name = mkdtemp(**kwargs)

        def __enter__(self):
            return self.name

        def __exit__(self, _type, _value, _traceback):
            self.cleanup()

        def cleanup(self):
            from shutil import rmtree
            if self.name is not None:
                rmtree(self.name)
