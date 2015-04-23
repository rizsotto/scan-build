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
import os.path
import sys
import time
import json
import tempfile
import multiprocessing
from analyzer import tempdir
from analyzer.decorators import to_logging_level, trace
from analyzer.runner import run
from analyzer.bear import main as intercept
from analyzer.options import create_parser
from analyzer.report import document
from analyzer.clang import get_checkers


def main():
    def run_analyze(args):
        return args.subparser_name in {'run', 'analyze'}

    def run_intercept(args):
        return args.subparser_name in {'run', 'intercept'}

    try:
        program = os.path.basename(sys.argv[0])
        logging.basicConfig(
            format='{0}: %(levelname)s: %(message)s'.format(program))

        parser = create_parser()
        args = parser.parse_args()

        logging.getLogger().setLevel(to_logging_level(args.verbose))
        logging.debug('Parsed arguments: '.format(args))

        if run_analyze(args):
            if args.help_checkers_verbose:
                print_checkers(get_checkers(args.clang, args.plugins))
                return 0
            elif args.help_checkers:
                print_active_checkers(get_checkers(args.clang, args.plugins))
                return 0
            # hack the cdb parameter in args when that is not a parameter.
            elif args.subparser_name == 'run':
                args.cdb = 'compile_commands.json'

            exit_code = intercept(args) if run_intercept(args) else 0
            with ReportDirectory(args.output, args.keep_empty) as target_dir:
                run_analyzer(args, target_dir.name)
                number_of_bugs = document(args, target_dir.name)

                # remove cdb when that is not a parameter.
                if args.subparser_name == 'run':
                    os.unlink(args.cdb)

                return number_of_bugs if args.status_bugs else exit_code

        elif run_intercept(args):
            return intercept(args)

    except KeyboardInterrupt:
        return 1
    except Exception as exception:
        logging.exception("Something unexpected had happened.")
        return 127


@trace
def run_analyzer(args, out_dir):
    """ Runs the analyzer.

    It generates commands (from compilation database entries) which contains
    enough information to run the analyzer (and the crash report generation
    if that was requested). """

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


@trace
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
