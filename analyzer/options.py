# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

""" This module implements a command line parser based on argparse.

Since 'argparse' module is available only 2.7 and afterwards, this is
the major force to be compatible with newer versions only. """

import argparse
from analyzer import tempdir


def create_parser(program):
    """ Parser factory method. """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False)

    option_builders = {
        'bear': [_common, _bear, _bear_only],
        'beye': [_common, _beye],
        'scan-build': [_common, _bear, _beye]}

    for builder in option_builders[program]:
        builder(parser)

    return parser


def _common(parser):
    parser.add_argument(
        '--help', '-h',
        action='store_true',
        dest='help',
        help="""show this help message and exit""")
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help="""Enable verbose output from '%(prog)s'. A second and third
                '-v' increases verbosity.""")
    parser.add_argument(
        '--cdb',
        metavar='<file>',
        default="compile_commands.json",
        help="""The JSON compilation database.""")


def _bear(parser):
    parser.add_argument(
        dest='build',
        nargs=argparse.REMAINDER,
        help="""Command to run.""")


def _bear_only(parser):
    advanced = parser.add_argument_group('advanced options')
    advanced.add_argument(
        '--append',
        action='store_true',
        help="""Append new entries to existing compilation database.""")
    advanced.add_argument(
        '--disable-filter', '-n',
        dest='raw_entries',
        action='store_true',
        help="""Disable filter, unformated output.""")


def _beye(parser):
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
    parser.add_argument(
        '--sequential',
        action='store_true',
        help="""Execute analyzer sequentialy.""")
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
        help="""This option outputs the results as a set of .html and .plist
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
