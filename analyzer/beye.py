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
import json
import os
import time
import functools
import tempfile
import shutil
import multiprocessing
from analyzer import tempdir
from analyzer.options import create_parser
from analyzer.decorators import to_logging_level, trace, require, entry
from analyzer.command import create
from analyzer.runner import run
from analyzer.report import generate_cover, count_bugs
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


def main(parser, build_ear):
    """ The reusable entry point of 'beye'.

    The 'scan-build' and 'beye' are the two entry points of this code.

    parser      -- the command line parser.
    build_ear   -- the compilation database builder function. """

    def cover_file_asked(output_format):
        """ Cover report can be generated only from html files. """
        return 'html' == output_format or 'plist-html' == output_format

    args = parser.parse_args()

    logging.getLogger().setLevel(to_logging_level(args.verbose))
    logging.debug(args)

    if args.help:
        parser.print_help()
        return print_checkers(get_checkers(args.clang, args.plugins))
    elif args.help_checkers:
        return print_checkers(get_checkers(args.clang, args.plugins), True)

    exit_code = build_ear(args)
    with ReportDirectory(args.output, args.keep_empty) as target_dir:
        run_analyzer(args, target_dir.name)
        number_of_bugs = count_bugs(target_dir.name)
        if cover_file_asked(args.output_format) and number_of_bugs > 0:
            generate_cover(
                {'out_dir': target_dir.name,
                 'in_cdb': args.cdb,
                 'clang': args.clang,
                 'html_title': args.html_title})
            shutil.copy(args.cdb, target_dir.name)

        return number_of_bugs if args.status_bugs else exit_code


@trace
@require(['cdb', 'sequential'])
def run_analyzer(args, out_dir):
    """ Runs the analyzer.

    First it generates the command which will be executed. But not all
    compilation database entry makes an analyzer call. Result of that
    step contains enough information to run the analyzer (and the crash
    report generation if that was requested). """

    def analyzer_params(args):
        """ A group of command line arguments can mapped to command
        line arguments of the analyzer. This method generates those. """
        result = []

        extend_result = lambda pieces, prefix: \
            functools.reduce(lambda acc, x: acc + [prefix, x], pieces, result)

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
            extend_result(args.plugins, '-load')
        if args.enable_checker:
            extend_result(args.enable_checker, '-analyzer-checker')
        if args.disable_checker:
            extend_result(args.disable_checker, '-analyzer-disable-checker')
        if args.ubiviz:
            result.append('-analyzer-viz-egraph-ubigraph')
        return functools.reduce(
            lambda acc, x: acc + ['-Xclang', x], result, [])

    def wrap(iterable, const):
        for current in iterable:
            current.update(const)
            yield current

    with open(args.cdb, 'r') as handle:
        pool = multiprocessing.Pool(1 if args.sequential else None)
        commands = [cmd
                    for cmd
                    in pool.imap_unordered(
                        create,
                        wrap(json.load(handle), {
                            'clang': args.clang,
                            'direct_args': analyzer_params(args)}))
                    if cmd is not None]

        for current in pool.imap_unordered(
                run,
                wrap(commands, {
                    'out_dir': out_dir,
                    'report_failures': args.report_failures,
                    'output_format': args.output_format})):
            if current is not None:
                for line in current['error_output']:
                    logging.info(line.rstrip())
        pool.close()
        pool.join()


@trace
def print_checkers(checkers, only_actives=False):
    """ Print checker help to stdout. """
    def dump(message):
        if not only_actives:
            print(os.linesep + message + os.linesep)

    dump('available checkers:')
    for name in sorted(checkers.keys()):
        description, active = checkers[name]
        if only_actives:
            if active:
                print(name)
        else:
            prefix = '+' if active else ' '
            if len(name) > 30:
                print(' {0} {1}'.format(prefix, name))
                print(' ' * 35 + description)
            else:
                print(' {0} {1: <30}  {2}'.format(prefix, name, description))
    dump('NOTE: "+" indicates that an analysis is enabled by default.')

    return 0


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
