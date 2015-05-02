# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

""" This module implements the 'scan-build' command API.

To run the static analyzer against a build is done in multiple steps:

 -- Intercept: capture the compilation command during the build,
 -- Analyze:   run the analyzer against the captured commands,
 -- Report:    create a cover report from the analyzer outputs.  """


import logging
import sys
import os
import os.path
import time
import json
import tempfile
import argparse
import multiprocessing
from libscanbuild import tempdir
from libscanbuild.runner import run
from libscanbuild.intercept import capture
from libscanbuild.options import create_parser
from libscanbuild.report import document
from libscanbuild.clang import get_checkers


__all__ = ['main']


def main():
    """ Entry point for 'scan-build'. """

    try:
        parser = create_parser()
        args = parser.parse_args()
        validate(parser, args)

        initialize_logging(args)
        logging.debug('Parsed arguments: {0} '.format(args))

        # run build command and capture compiler executions
        exit_code = capture(args) if args.action in {'all', 'intercept'} else 0
        # when we only do interception the job is done
        if args.action == 'intercept':
            return exit_code
        # next step to run the analyzer against the captured commands
        with ReportDirectory(args.output, args.keep_empty) as target_dir:
            run_analyzer(args, target_dir.name)
            # cover report generation and bug counting
            number_of_bugs = document(args, target_dir.name)
            # set exit status as it was requested
            return number_of_bugs if args.status_bugs else exit_code

    except KeyboardInterrupt:
        return 1
    except Exception:
        logging.exception("Something unexpected had happened.")
        return 127


def initialize_logging(args):
    """ Logging format controlled by the 'verbose' command line argument. """

    fmt_string = '{0}: %(levelname)s: %(message)s'

    if 0 == args.verbose:
        level = logging.WARNING
    elif 1 == args.verbose:
        level = logging.INFO
    elif 2 == args.verbose:
        level = logging.DEBUG
    else:
        level = logging.DEBUG
        fmt_string = '{0}: %(levelname)s: %(funcName)s: %(message)s'

    program = os.path.basename(sys.argv[0])
    logging.basicConfig(format=fmt_string.format(program), level=level)


def validate(parser, args):
    """ Validation done by the parser itself, but semantic check still
    needs to be done. This method is doing that. """

    if not args.action:
        parser.error('missing action')

    if args.action in {'all', 'analyze'}:
        if args.help_checkers_verbose:
            print_checkers(get_checkers(args.clang, args.plugins))
            parser.exit()
        elif args.help_checkers:
            print_active_checkers(get_checkers(args.clang, args.plugins))
            parser.exit()

    if args.action in {'all', 'intercept'} and not args.build:
        parser.error('missing build command')


def run_analyzer(args, out_dir):
    """ Runs the analyzer against the given compilation database. """

    def extend(current, const):
        current.update(const)
        return current

    consts = {'out_dir': out_dir,
              'direct_args': analyzer_params(args),
              'clang': args.clang,
              'report_failures': args.report_failures,
              'output_format': args.output_format}

    with open(args.cdb, 'r') as handle:
        generator = (extend(cmd, consts) for cmd in json.load(handle))

        pool = multiprocessing.Pool(1 if 2 <= args.verbose else None)
        for current in pool.imap_unordered(run, generator):
            if current is not None:
                for line in current['error_output']:
                    logging.info(line.rstrip())
        pool.close()
        pool.join()


def analyzer_params(args):
    """ A group of command line arguments can mapped to command
    line arguments of the analyzer. This method generates those. """

    def prefix_with(constant, pieces):
        return [elem for piece in pieces for elem in [constant, piece]]

    result = []

    if args.store_model:
        result.append('-analyzer-store={0}'.format(args.store_model))
    if args.constraints_model:
        result.append(
            '-analyzer-constraints={0}'.format(args.constraints_model))
    if args.internal_stats:
        result.append('-analyzer-stats')
    if args.analyze_headers:
        result.append('-analyzer-opt-analyze-headers')
    if args.stats:
        result.append('-analyzer-checker=debug.Stats')
    if args.maxloop:
        result.extend(['-analyzer-max-loop', str(args.maxloop)])
    if args.output_format:
        result.append('-analyzer-output={0}'.format(args.output_format))
    if args.analyzer_config:
        result.append(args.analyzer_config)
    if 2 <= args.verbose:
        result.append('-analyzer-display-progress')
    if args.plugins:
        result.extend(prefix_with('-load', args.plugins))
    if args.enable_checker:
        result.extend(prefix_with('-analyzer-checker', args.enable_checker))
    if args.disable_checker:
        result.extend(
            prefix_with('-analyzer-disable-checker', args.disable_checker))
    if os.getenv('UBIVIZ'):
        result.append('-analyzer-viz-egraph-ubigraph')

    return prefix_with('-Xclang', result)


def print_active_checkers(checkers):
    """ Print active checkers to stdout. """

    for name in sorted(name
                       for name, (_, active)
                       in checkers.items()
                       if active):
        print(name)


def print_checkers(checkers):
    """ Print verbose checker help to stdout. """

    print('')
    print('available checkers:')
    print('')
    for name in sorted(checkers.keys()):
        description, active = checkers[name]
        prefix = '+' if active else ' '
        if len(name) > 30:
            print(' {0} {1}'.format(prefix, name))
            print(' ' * 35 + description)
        else:
            print(' {0} {1: <30}  {2}'.format(prefix, name, description))
    print('')
    print('NOTE: "+" indicates that an analysis is enabled by default.')
    print('')


class ReportDirectory(object):
    """ Responsible for the report directory.

    hint -- could specify the parent directory of the output directory.
    keep -- a boolean value to keep or delete the empty report directory. """

    def __init__(self, hint, keep):
        self.name = ReportDirectory._create(hint)
        self.keep = keep

    def __enter__(self):
        return self

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
