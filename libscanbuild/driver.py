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
import re
import os
import os.path
import time
import json
import tempfile
import multiprocessing
from libscanbuild.runner import run
from libscanbuild.intercept import capture
from libscanbuild.options import create_parser
from libscanbuild.report import document
from libscanbuild.clang import get_checkers

__all__ = ['main']


def main(bin_dir):
    """ Entry point for 'scan-build'. """

    try:
        parser = create_parser()
        args = parser.parse_args()
        validate(parser, args)
        # setup logging
        initialize_logging(args)
        logging.debug('Parsed arguments: %s', args)

        # run build command and capture compiler executions
        exit_code = capture(args, bin_dir) \
            if args.action in {'all', 'intercept'} else 0
        # when we only do interception the job is done
        if args.action == 'intercept':
            return exit_code

        # next step to run the analyzer against the captured commands
        with ReportDirectory(args.output, args.keep_empty) as target_dir:
            if args.action == 'analyze' or need_analyzer(args.build):
                run_analyzer(args, target_dir.name)
                # cover report generation and bug counting
                number_of_bugs = document(args, target_dir.name, True)
                # remove the compilation database when it was not requested
                if args.action == 'all' and os.path.exists(args.cdb):
                    os.unlink(args.cdb)
                # set exit status as it was requested
                return number_of_bugs if args.status_bugs else exit_code
            else:
                return exit_code
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


def need_analyzer(args):
    """ Check the internt of the build command. """

    return len(args) and not re.search('configure|autogen', args[0])


def run_analyzer(args, output_dir):
    """ Runs the analyzer against the given compilation database. """

    def exclude(filename):
        """ Return true when any excluded directory prefix the filename. """
        return any(re.match(r'^' + directory, filename)
                   for directory in args.excludes)

    consts = {
        'clang': args.clang,
        'output_dir': output_dir,
        'output_format': args.output_format,
        'report_failures': args.report_failures,
        'direct_args': analyzer_params(args)
    }

    with open(args.cdb, 'r') as handle:
        generator = (dict(cmd, **consts) for cmd in json.load(handle)
                     if not exclude(cmd['file']))
        # when verbose output requested execute sequentially
        pool = multiprocessing.Pool(1 if 2 < args.verbose else None)
        for current in pool.imap_unordered(run, generator):
            if current is not None:
                # display error message from the static analyzer
                for line in current['error_output']:
                    logging.info(line.rstrip())
        pool.close()
        pool.join()


def analyzer_params(args):
    """ A group of command line arguments can mapped to command
    line arguments of the analyzer. This method generates those. """

    def prefix_with(constant, pieces):
        """ From a sequence create another sequence where every second element
        is from the original sequence and the odd elements are the prefix.

        eg.: prefix_with(0, [1,2,3]) creates [0, 1, 0, 2, 0, 3] """

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
    if 4 <= args.verbose:
        result.append('-analyzer-display-progress')
    if args.plugins:
        result.extend(prefix_with('-load', args.plugins))
    if args.enable_checker:
        checkers = ','.join(args.enable_checker)
        result.extend(['-analyzer-checker', checkers])
    if args.disable_checker:
        checkers = ','.join(args.disable_checker)
        result.extend(['-analyzer-disable-checker', checkers])
    if os.getenv('UBIVIZ'):
        result.append('-analyzer-viz-egraph-ubigraph')

    return prefix_with('-Xclang', result)


def print_active_checkers(checkers):
    """ Print active checkers to stdout. """

    for name in sorted(name for name, (_, active) in checkers.items()
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
        logging.info('Report directory created: %s', self.name)

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        if os.listdir(self.name):
            msg = "Run 'scan-view %s' to examine bug reports."
            self.keep = True
        else:
            if self.keep:
                msg = "Report directory '%s' contans no report, but kept."
            else:
                msg = "Removing directory '%s' because it contains no report."
        logging.warning(msg, self.name)

        if not self.keep:
            os.rmdir(self.name)

    @staticmethod
    def _create(hint):
        stamp = time.strftime('scan-build-%Y-%m-%d-%H%M%S-', time.localtime())
        return tempfile.mkdtemp(prefix=stamp, dir=hint)
