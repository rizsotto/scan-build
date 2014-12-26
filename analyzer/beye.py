# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

""" This module is responsible to run the analyzer against a compilation
database.

This is done by revisit each entry in the database and run only the analyzer
against that file. The output of the analyzer is directed into a result folder,
which is post-processed for a "cover" generation. (There is a bit terminology
confusion here. I would rather say the 'scan-build' generates a report on the
build. While 'clang' is also generates report on individual files. To avoid
confusion the 'scan-build' generated report I call "cover".) """


import logging
import os
import time
import tempfile
import multiprocessing
from analyzer import tempdir
from analyzer.options import create_parser
from analyzer.decorators import to_logging_level, trace, entry
from analyzer.command import generate_commands
from analyzer.runner import run
from analyzer.report import document
from analyzer.clang import get_checkers


@entry
def scanbuild():
    """ Entry point for 'scan-build' command.

    This method combines the 'bear' and 'beye' commands to imitate the
    original Perl implementation of 'scan-build' command. """

    from analyzer.bear import main as run_bear
    parser = create_parser('scan-build')
    return main(parser, run_bear)


@entry
def beye():
    """ Entry point for 'beye' command.

    It takes a compilation database as input and run analyzer against each
    files. The logic to run analyzer against a single file is implemented in
    several modules. """

    parser = create_parser('beye')
    return main(parser, lambda x: 0)


def main(parser, intercept):
    """ The reusable entry point of 'beye'.

    The 'scan-build' and 'beye' are the two entry points of this code.

    parser      -- the command line parser.
    intercept   -- the compilation database builder function. """

    args = parser.parse_args()

    logging.getLogger().setLevel(to_logging_level(args.verbose))
    logging.debug(args)

    if args.help:
        parser.print_help()
        print_checkers(get_checkers(args.clang, args.plugins))
        return 0
    elif args.help_checkers:
        print_active_checkers(get_checkers(args.clang, args.plugins))
        return 0

    exit_code = intercept(args)
    with ReportDirectory(args.output, args.keep_empty) as target_dir:
        run_analyzer(args, target_dir.name)
        number_of_bugs = document(args, target_dir.name)

        return number_of_bugs if args.status_bugs else exit_code


@trace
def run_analyzer(args, out_dir):
    """ Runs the analyzer.

    It generates commands (from compilation database entries) which contains
    enough information to run the analyzer (and the crash report generation
    if that was requested). """

    def wrap(iterable, const):
        for current in iterable:
            current.update(const)
            yield current

    pool = multiprocessing.Pool(1 if args.sequential else None)
    for current in pool.imap_unordered(
            run,
            wrap(generate_commands(args), {
                'out_dir': out_dir,
                'clang': args.clang,
                'report_failures': args.report_failures,
                'output_format': args.output_format})):
        if current is not None:
            for line in current['error_output']:
                logging.info(line.rstrip())
    pool.close()
    pool.join()


@trace
def print_active_checkers(checkers):
    """ Print active checkers to stdout. """
    for name in sorted(name
                       for name, (_, active)
                       in checkers.items()
                       if active):
        print(name)


@trace
def print_checkers(checkers):
    """ Print checker help to stdout. """
    print()
    print('available checkers:')
    print()
    for name in sorted(checkers.keys()):
        description, active = checkers[name]
        prefix = '+' if active else ' '
        if len(name) > 30:
            print(' {0} {1}'.format(prefix, name))
            print(' ' * 35 + description)
        else:
            print(' {0} {1: <30}  {2}'.format(prefix, name, description))
    print()
    print('NOTE: "+" indicates that an analysis is enabled by default.')
    print()


class ReportDirectory(object):
    """ Responsible for the report directory.

    hint -- could specify the parent directory of the output directory.
    keep -- a boolean value to keep or delete the empty report directory. """

    def __init__(self, hint, keep):
        self.name = ReportDirectory._create(hint)
        self.keep = keep

    def __enter__(self):
        return self

    @trace
    def __exit__(self, _type, _value, _traceback):
        if os.listdir(self.name):
            msg = "Run 'scan-view {0}' to examine bug reports."
            self.keep = True
        else:
            if self.keep:
                msg = "Report directory '{0}' contans no report, but kept."
            else:
                msg = "Removing directory '{0}' because it contains no report."
        logging.warning(msg.format(self.name))

        if not self.keep:
            os.rmdir(self.name)

    @staticmethod
    def _create(hint):
        if tempdir() != hint:
            try:
                os.mkdir(hint)
                return hint
            except OSError:
                raise
        else:
            stamp = time.strftime('%Y-%m-%d-%H%M%S', time.localtime())
            return tempfile.mkdtemp(prefix='scan-build-{0}-'.format(stamp))
