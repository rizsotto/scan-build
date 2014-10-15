# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import json
import os
import time
import functools
import tempfile
import multiprocessing
from analyzer import create_parser
from analyzer.decorators import to_logging_level, trace, require, entry
from analyzer.command import create
from analyzer.runner import run
from analyzer.report import generate_report, count_bugs
from analyzer.clang import get_checkers


@entry
def scanbuild():
    from analyzer.bear import main as run_bear
    from analyzer.bear import initialize_command_line as bear_command_init
    parser = bear_command_init(initialize_command_line(create_parser()))
    return main(parser, run_bear)


@entry
def beye():
    parser = initialize_command_line(create_parser())
    return main(parser, lambda x: 0)


def main(parser, build_ear):
    """ Entry point for 'beye'.

    'beye' is orchestrating to run the analyzer against the given project
    and generates report file (if that was also requested).

    Currently it takes a compilation database as input and run analyzer
    against each files.

    The logic to run analyzer against a single file is implemented in several
    modules. One generates the command from a single compiler call. This is
    in the 'analyzer.command' module. The 'analyzer.runner' executes the
    command.

    Report generation logic is in a separate module called 'analyzer.report'.
    """
    def needs_report_file(output_format):
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
    with ReportDirectory(args.output, args.keep_empty) as out_dir:
        run_analyzer(args, out_dir)
        number_of_bugs = generate_report(
            {'sequential': args.sequential,
             'out_dir': out_dir,
             'prefix': get_prefix_from(args.cdb),
             'clang': args.clang,
             'html_title': args.html_title}) \
            if needs_report_file(args.output_format) else count_bugs(out_dir)

        return number_of_bugs if args.status_bugs else exit_code


@trace
def initialize_command_line(parser):
    """ Parse command line and return a dictionary of given values.

    Command line parameters are defined by previous implementation, and
    influence either the analyzer behaviour or the report generation.
    The paramters are grouped together according their functionality.

    The help message is generated from this parse method. Default values
    are also printed. """
    parser.add_argument(
        '--output', '-o',
        metavar='<path>',
        default=tempdir(),
        help="""Specifies the output directory for analyzer reports.
                Subdirectory will be created if default directory is targeted.
                """)
    parser.add_argument(
        '--status-bugs',
        action='store_true',
        help="""By default, the exit status of '%(prog)s' is the same as the
                executed build command. Specifying this option causes the exit
                status of '%(prog)s' to be non zero if it found potential bugs
                and zero otherwise.""")
    parser.add_argument(
        '--html-title',
        metavar='<title>',
        help="""Specify the title used on generated HTML pages.
                If not specified, a default title will be used.""")
    parser.add_argument(
        '--analyze-headers',
        action='store_true',
        help="""Also analyze functions in #included files. By default, such
                functions are skipped unless they are called by functions
                within the main source file.""")
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        '--plist',
        dest='output_format',
        const='plist',
        default='html',
        action='store_const',
        help="""This option outputs the results as a set of .plist files.""")
    format_group.add_argument(
        '--plist-html',
        dest='output_format',
        const='plist-html',
        default='html',
        action='store_const',
        help="""This option outputs the results as a set of HTML and .plist
                files.""")
    # TODO: implement '-view '

    advanced = parser.add_argument_group('advanced options')
    advanced.add_argument(
        '--keep-empty',
        action='store_true',
        help="""Don't remove the build results directory even if no issues
                were reported.""")
    advanced.add_argument(
        '--no-failure-reports',
        dest='report_failures',
        action='store_false',
        help="""Do not create a 'failures' subdirectory that includes analyzer
                crash reports and preprocessed source files.""")
    advanced.add_argument(
        '--stats',
        action='store_true',
        help="""Generates visitation statistics for the project being analyzed.
                """)
    advanced.add_argument(
        '--internal-stats',
        action='store_true',
        help="""Generate internal analyzer statistics.""")
    advanced.add_argument(
        '--maxloop',
        metavar='<loop count>',
        type=int,
        default=4,
        help="""Specifiy the number of times a block can be visited before
                giving up. Increase for more comprehensive coverage at a cost
                of speed.""")
    advanced.add_argument(
        '--store',
        metavar='<model>',
        dest='store_model',
        default='region',
        choices=['region', 'basic'],
        help="""Specify the store model used by the analyzer.
                'region' specifies a field- sensitive store model.
                'basic' which is far less precise but can more quickly
                analyze code. 'basic' was the default store model for
                checker-0.221 and earlier.""")
    advanced.add_argument(
        '--constraints',
        metavar='<model>',
        dest='constraints_model',
        default='range',
        choices=['range', 'basic'],
        help="""Specify the contraint engine used by the analyzer. Specifying
                'basic' uses a simpler, less powerful constraint model used by
                checker-0.160 and earlier.""")
    advanced.add_argument(
        '--use-analyzer',
        metavar='<path>',
        dest='clang',
        default='clang',
        help="""'%(prog)s' uses the 'clang' executable relative to itself for
                static analysis. One can override this behavior with this
                option by using the 'clang' packaged with Xcode (on OS X) or
                from the PATH.""")
    advanced.add_argument(
        '--analyzer-config',
        metavar='<options>',
        help="""Provide options to pass through to the analyzer's
                -analyzer-config flag. Several options are separated with
                comma: 'key1=val1,key2=val2'

                Available options:
                    stable-report-filename=true or false (default)

                Switch the page naming to:
                report-<filename>-<function/method name>-<id>.html
                instead of report-XXXXXX.html""")
    advanced.add_argument(
        '--ubiviz',
        action='store_true',
        help="""Meant to display the analysis path graph (aka 'exploded graph')
                as it gets explored by the analyzer. The ubigraph support is
                not enabled in a release build of clang. And you also need the
                'ubiviz' script in your path.""")

    plugins = parser.add_argument_group('checker options')
    plugins.add_argument(
        '--load-plugin',
        metavar='<plugin library>',
        dest='plugins',
        action='append',
        help="""Loading external checkers using the clang plugin interface.""")
    plugins.add_argument(
        '--enable-checker',
        metavar='<checker name>',
        action='append',
        help="""Enable specific checker.""")
    plugins.add_argument(
        '--disable-checker',
        metavar='<checker name>',
        action='append',
        help="""Disable specific checker.""")
    plugins.add_argument(
        '--help-checkers',
        action='store_true',
        help="""A default group of checkers is run unless explicitly disabled.
                Exactly which checkers constitute the default group is a
                function of the operating system in use. These can be printed
                with this flag.""")

    return parser


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
def get_prefix_from(compilation_database):
    """ Get common path prefix for compilation database entries.
    This will be used to taylor the file names in the final report. """
    def common(files):
        result = None
        for current in files:
            result = current if result is None else\
                os.path.commonprefix([result, current])

        if result is None:
            return ''
        elif not os.path.isdir(result):
            return os.path.dirname(result)
        else:
            return result

    def filenames():
        with open(compilation_database, 'r') as handle:
            for element in json.load(handle):
                yield os.path.dirname(element['file'])

    return common(filenames())


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
        return self.name

    @trace
    def __exit__(self, _type, _value, _traceback):
        if os.listdir(self.name):
            msg = "Run 'scan-view {0}' to examine bug reports."
        else:
            if self.keep:
                msg = "Report directory '{0}' contans no report, but kept."
            else:
                os.rmdir(self.name)
                msg = "Removing directory '{0}' because it contains no report."
        logging.warning(msg.format(self.name))

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
            return tempfile.mkdtemp(prefix='beye-{0}-'.format(stamp))


def tempdir():
    return os.getenv('TMPDIR', os.getenv('TEMP', os.getenv('TMP', '/tmp')))
