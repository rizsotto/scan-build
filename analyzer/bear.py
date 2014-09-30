# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import multiprocessing
import subprocess
import argparse
import json
import re
import os
import os.path
import sys
import glob
import pkg_resources
from analyzer.decorators import trace


if 'darwin' == sys.platform:
    ENVIRONMENTS = [("ENV_OUTPUT", "BEAR_OUTPUT"),
                    ("ENV_PRELOAD", "DYLD_INSERT_LIBRARIES"),
                    ("ENV_FLAT", "DYLD_FORCE_FLAT_NAMESPACE")]
else:
    ENVIRONMENTS = [("ENV_OUTPUT", "BEAR_OUTPUT"),
                    ("ENV_PRELOAD", "LD_PRELOAD")]


if sys.version_info.major >= 3 and sys.version_info.minor >= 2:
    from tempfile import TemporaryDirectory
else:
    class TemporaryDirectory(object):

        def __init__(self, **kwargs):
            from tempfile import mkdtemp
            self.name = mkdtemp(*kwargs)

        def __enter__(self):
            return self.name

        def __exit__(self, _type, _value, _traceback):
            self.cleanup()

        def cleanup(self):
            from shutil import rmtree
            if self.name is not None:
                rmtree(self.name)


def main():
    multiprocessing.freeze_support()
    logging.basicConfig(format='bear: %(message)s')

    def from_number_to_level(num):
        if 0 == num:
            return logging.WARNING
        elif 1 == num:
            return logging.INFO
        elif 2 == num:
            return logging.DEBUG
        else:
            return 5  # used by the trace decorator

    try:
        parser = create_command_line_parser()
        args = parser.parse_args()

        logging.getLogger().setLevel(from_number_to_level(args.verbose))
        logging.debug(args)

        exit_code = 0
        with TemporaryDirectory(prefix='bear-') as tmpdir:
            exit_code = run_build(args.build, tmpdir)
            commands = list(collect(not args.filtering, tmpdir))
            with open(args.output, 'w+') as handle:
                json.dump(commands, handle, sort_keys=True, indent=4)
        return exit_code

    except Exception as exception:
        print(str(exception))
        return 127


@trace
def create_command_line_parser():
    """ Parse command line and return a dictionary of given values. """
    parser = argparse.ArgumentParser(
        prog='bear',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-o', '--output',
        metavar='<file>',
        dest='output',
        default="compile_commands.json",
        help="""Specifies the output directory for analyzer reports.
             Subdirectory will be created if default directory is targeted.""")
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="""Enable verbose output from ‘bear’. A second and third '-v'
             increases verbosity.""")
    parser.add_argument(
        dest='build',
        nargs=argparse.REMAINDER,
        help="""Command to run.""")

    group2 = parser.add_argument_group('ADVANCED OPTIONS')
    group2.add_argument(
        '-n', '--disable-filter',
        dest='filtering',
        action='store_true',
        help="""Disable filter, unformated output.""")

    return parser


@trace
def run_build(command, destination):
    def get_ear_so_file():
        path = pkg_resources.get_distribution('beye').location
        candidates = glob.glob(os.path.join(path, 'ear*.so'))
        return candidates[0] if len(candidates) else None

    environment = dict(os.environ)
    for alias, key in ENVIRONMENTS:
        value = '1'
        if alias == 'ENV_PRELOAD':
            value = get_ear_so_file()
        elif alias == 'ENV_OUTPUT':
            value = destination
        environment.update({key: value})

    child = subprocess.Popen(command, env=environment, shell=True)
    child.wait()
    return child.returncode


@trace
def collect(filtering, destination):
    def parse(filename):
        RS = chr(0x1e)
        US = chr(0x1f)
        with open(filename, 'r') as handler:
            content = handler.read()
            records = content.split(RS)
            return {'pid': records[0],
                    'ppid': records[1],
                    'function': records[2],
                    'directory': records[3],
                    'command': records[4].split(US)[:-1]}

    def match_compiler(record):
        patterns = [
            re.compile(r'^([^/]*/)*c(c|\+\+)$'),
            re.compile(r'^([^/]*/)*([^-]*-)*g(cc|\+\+)(-[34].[0-9])?$'),
            re.compile(r'^([^/]*/)*clang(\+\+)?(-[23].[0-9])?$'),
            re.compile(r'^([^/]*/)*llvm-g(cc|\+\+)$'),
        ]
        executable = record['command'][0]
        for pattern in patterns:
            if pattern.match(executable):
                return record
        return None

    def match_cancel(record):
        patterns = [
            re.compile(r'^-cc1$')
        ]
        for arg in record['command']:
            for pattern in patterns:
                if pattern.match(arg):
                    return None
        return record

    generator = glob.iglob(os.path.join(destination, 'cmd.*'))
    functions = [parse, match_compiler, match_cancel] if filtering else [parse]
    for element in generator:
        for function in functions:
            element = function(element)
            if element is None:
                break
        if element is not None:
            yield element
