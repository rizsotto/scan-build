# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import multiprocessing
import subprocess
import json
import functools
import os
import time
import tempfile
from analyzer.decorators import trace, require
from analyzer.command import create
from analyzer.runner import run
from analyzer.report import generate_report
from analyzer.clang import get_checkers


def main():
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
    multiprocessing.freeze_support()
    logging.basicConfig(format='beye: %(message)s')

    def from_number_to_level(num):
        if 0 == num:
            return logging.WARNING
        elif 1 == num:
            return logging.INFO
        elif 2 == num:
            return logging.DEBUG
        else:
            return 5  # used by the trace decorator

    def needs_report_file(opts):
        output_format = opts.get('output_format')
        return 'html' == output_format or 'plist-html' == output_format

    try:
        parser = create_command_line_parser()
        args = parser.parse_args().__dict__

        logging.getLogger().setLevel(from_number_to_level(args['verbose']))
        logging.debug(args)

        if args['help']:
            parser.print_help()
            return print_checkers(get_checkers(args['clang'], args['plugins']))
        elif args['help_checkers']:
            return print_checkers(get_checkers(args['clang'], args['plugins']),
                                  True)

        with ReportDirectory(args['output'], args['keep_empty']) as out_dir:
            run_analyzer(args, out_dir)
            number_of_bugs = generate_report(
                {'sequential': args['sequential'],
                 'out_dir': out_dir,
                 'prefix': get_prefix_from(args['input']),
                 'clang': args['clang'],
                 'html_title': args['html_title']})\
                if needs_report_file(args) else 0
            # TODO get result from bear if --status-bugs were not requested
            return number_of_bugs if 'status_bugs' in args else 0

    except Exception as exception:
        print(str(exception))
        return 127


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


@trace
def create_command_line_parser():
    """ Parse command line and return a dictionary of given values.

    Command line parameters are defined by previous implementation, and
    influence either the analyzer behaviour or the report generation.
    The paramters are grouped together according their functionality.

    The help message is generated from this parse method. Default values
    are also printed. """
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(prog='beye',
                            add_help=False,
                            formatter_class=ArgumentDefaultsHelpFormatter)
    group1 = parser.add_argument_group('OPTIONS')
    group1.add_argument(
        '--help', '-h',
        action='store_true',
        dest='help',
        help="Print this message")
    group1.add_argument(
        '--input',
        metavar='<file>',
        default="compile_commands.json",
        help="The JSON compilation database.")
    group1.add_argument(
        '--output', '-o',
        metavar='<path>',
        default=tempdir(),
        help="""Specifies the output directory for analyzer reports.
             Subdirectory will be created if default directory is targeted.
             """)
    group1.add_argument(
        '--sequential',
        action='store_true',
        help="Execute analyzer sequentialy.")
    group1.add_argument(
        '--status-bugs',
        action='store_true',
        help='By default, the exit status of ‘beye’ is the same as the\
              executed build command. Specifying this option causes the exit\
              status of ‘beye’ to be 1 if it found potential bugs and 0\
              otherwise.')
    group1.add_argument(
        '--html-title',
        metavar='<title>',
        help='Specify the title used on generated HTML pages.\
              If not specified, a default title will be used.')
    group1.add_argument(
        '--analyze-headers',
        action='store_true',
        help='Also analyze functions in #included files. By default,\
              such functions are skipped unless they are called by\
              functions within the main source file.')
    format_group = group1.add_mutually_exclusive_group()
    format_group.add_argument(
        '--plist',
        dest='output_format',
        const='plist',
        default='html',
        action='store_const',
        help='This option outputs the results as a set of .plist files.')
    format_group.add_argument(
        '--plist-html',
        dest='output_format',
        const='plist-html',
        default='html',
        action='store_const',
        help='This option outputs the results as a set of HTML and .plist\
              files.')
    group1.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help="Enable verbose output from ‘beye’. A second and third '-v'\
              increases verbosity.")
    # TODO: implement '-view '

    group2 = parser.add_argument_group('ADVANCED OPTIONS')
    group2.add_argument(
        '--keep-empty',
        action='store_true',
        help="Don't remove the build results directory even if no issues were\
              reported.")
    group2.add_argument(
        '--no-failure-reports',
        dest='report_failures',
        action='store_false',
        help="Do not create a 'failures' subdirectory that includes analyzer\
              crash reports and preprocessed source files.")
    group2.add_argument(
        '--stats',
        action='store_true',
        help='Generates visitation statistics for the project being analyzed.')
    group2.add_argument(
        '--internal-stats',
        action='store_true',
        help='Generate internal analyzer statistics.')
    group2.add_argument(
        '--maxloop',
        metavar='<loop count>',
        type=int,
        default=4,
        help='Specifiy the number of times a block can be visited before\
              giving up. Increase for more comprehensive coverage at a cost\
              of speed.')
    group2.add_argument(
        '--store',
        metavar='<model>',
        dest='store_model',
        default='region',
        choices=['region', 'basic'],
        help='Specify the store model used by the analyzer.\
              ‘region’ specifies a field- sensitive store model.\
              ‘basic’ which is far less precise but can more quickly\
              analyze code. ‘basic’ was the default store model for\
              checker-0.221 and earlier.')
    group2.add_argument(
        '--constraints',
        metavar='<model>',
        dest='constraints_model',
        default='range',
        choices=['range', 'basic'],
        help='Specify the contraint engine used by the analyzer. Specifying\
              ‘basic’ uses a simpler, less powerful constraint model used by\
              checker-0.160 and earlier.')
    group2.add_argument(
        '--use-analyzer',
        metavar='<path>',
        dest='clang',
        default='clang',
        help="‘beye’ uses the ‘clang’ executable relative to itself for\
              static analysis. One can override this behavior with this\
              option by using the ‘clang’ packaged with Xcode (on OS X) or\
              from the PATH.")
    group2.add_argument(
        '--analyzer-config',
        metavar='<options>',
        help="Provide options to pass through to the analyzer's\
              -analyzer-config flag. Several options are separated with comma:\
              'key1=val1,key2=val2'\
              \
              Available options:\
                stable-report-filename=true or false (default)\
                Switch the page naming to:\
                report-<filename>-<function/method name>-<id>.html\
                instead of report-XXXXXX.html")
    group2.add_argument(
        '--ubiviz',
        action='store_true',
        help="""Meant to display the analysis path graph (aka 'exploded graph')
             as it gets explored by the analyzer. The ubigraph support is not
             enabled in a release build of clang. And you also need the
             'ubiviz' script in your path.""")

    group3 = parser.add_argument_group('CHECKER OPTIONS')
    group3.add_argument(
        '--load-plugin',
        metavar='<plugin library>',
        dest='plugins',
        action='append',
        help='Loading external checkers using the clang plugin interface.')
    group3.add_argument(
        '--enable-checker',
        metavar='<checker name>',
        action='append',
        help='Enable specific checker.')
    group3.add_argument(
        '--disable-checker',
        metavar='<checker name>',
        action='append',
        help='Disable specific checker.')
    group3.add_argument(
        '--help-checkers',
        action='store_true',
        help="""A default group of checkers is run unless explicitly disabled.
              Exactly which checkers constitute the default group is a
              function of the operating system in use. These can be printed
              with this flag.""")

    return parser


@trace
@require(['input', 'sequential'])
def run_analyzer(args, out_dir):
    """ Runs the analyzer.

    First it generates the command which will be executed. But not all
    compilation database entry makes an analyzer call. Result of that
    step contains enough information to run the analyzer (and the crash
    report generation if that was requested). """

    def uname():
        return subprocess.check_output(['uname', '-a']).decode('ascii')

    def analyzer_params(args):
        """ A group of command line arguments of 'beye' can mapped to command
        line arguments of the analyzer. This method generates those. """
        opts = {k: v for k, v in args.items() if v is not None}
        result = []
        if 'store_model' in opts:
            result.append('-analyzer-store={0}'.format(opts['store_model']))
        if 'constraints_model' in opts:
            result.append(
                '-analyzer-constraints={0}'.format(opts['constraints_model']))
        if 'internal_stats' in opts and opts['internal_stats']:
            result.append('-analyzer-stats')
        if 'analyze_headers' in opts and opts['analyze_headers']:
            result.append('-analyzer-opt-analyze-headers')
        if 'stats' in opts and opts['stats']:
            result.append('-analyzer-checker=debug.Stats')
        if 'maxloop' in opts:
            result.extend(['-analyzer-max-loop', str(opts['maxloop'])])
        if 'output_format' in opts:
            result.append('-analyzer-output={0}'.format(opts['output_format']))
        if 'analyzer_config' in opts:
            result.append(opts['analyzer_config'])
        if 'verbose' in opts and 2 <= opts['verbose']:
            result.append('-analyzer-display-progress')
        if 'plugins' in opts:
            result = functools.reduce(
                lambda acc, x: acc + ['-load', x],
                opts['plugins'],
                result)
        if 'enable_checker' in opts:
            result = functools.reduce(
                lambda acc, x: acc + ['-analyzer-checker', x],
                opts['enable_checker'],
                result)
        if 'disable_checker' in opts:
            result = functools.reduce(
                lambda acc, x: acc + ['-analyzer-disable-checker', x],
                opts['disable_checker'],
                result)
        if 'ubiviz' in opts and opts['ubiviz']:
            result.append('-analyzer-viz-egraph-ubigraph')
        return functools.reduce(
            lambda acc, x: acc + ['-Xclang', x], result, [])

    def wrap(iterable, const):
        for current in iterable:
            current.update(const)
            yield current

    with open(args['input'], 'r') as handle:
        pool = multiprocessing.Pool(1 if args['sequential'] else None)
        commands = [cmd
                    for cmd
                    in pool.imap_unordered(
                        create,
                        wrap(json.load(handle), {
                            'clang': args['clang'],
                            'direct_args': analyzer_params(args)}))
                    if cmd is not None]

        for current in pool.imap_unordered(
                run,
                wrap(commands, {
                    'out_dir': out_dir,
                    'report_failures': args['report_failures'],
                    'output_format': args['output_format'],
                    'uname': uname()})):
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
            for entry in json.load(handle):
                yield os.path.dirname(entry['file'])

    return common(filenames())


@trace
def print_checkers(checkers, only_actives=False):
    """ Print checker help to stdout. """
    def dump(message):
        if not only_actives:
            print(os.linesep + message + os.linesep)

    dump('AVAILABLE CHECKERS:')
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


def tempdir():
    return os.getenv('TMPDIR', os.getenv('TEMP', os.getenv('TMP', '/tmp')))
