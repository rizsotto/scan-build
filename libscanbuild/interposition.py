# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import os
import sys
import argparse
import subprocess
import logging
from libscanbuild.options import (common_parameters, analyze_parameters,
                                  build_command)
from libscanbuild.driver import (initialize_logging, ReportDirectory,
                                 analyzer_params, print_checkers,
                                 print_active_checkers)
from libscanbuild.report import document
from libscanbuild.clang import get_checkers
from libscanbuild.runner import action_check
from libscanbuild.intercept import is_source_file
from libscanbuild.command import classify_parameters

__all__ = ['main', 'wrapper']


def main(bin_dir):
    """ Entry point for 'analyze-build'. """

    try:
        args = parse_and_validate_arguments()
        # setup logging
        initialize_logging(args)
        logging.debug('Parsed arguments: %s', args)
        # run the build
        with ReportDirectory(args.output, args.keep_empty) as target_dir:
            # run the build command
            environment = setup_environment(args, target_dir.name, bin_dir)
            logging.debug('run build in environment: %s', environment)
            exit_code = subprocess.call(args.build, env=environment)
            logging.debug('build finished with exit code: %d', exit_code)
            # cover report generation and bug counting
            number_of_bugs = document(args, target_dir.name, False)
            # set exit status as it was requested
            return number_of_bugs if args.status_bugs else exit_code
    except KeyboardInterrupt:
        return 1
    except Exception:
        logging.exception("Something unexpected had happened.")
        return 127


def parse_and_validate_arguments():
    """ Parse and validate command line arguments. """

    # create parser..
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    common_parameters(parser, False)
    analyze_parameters(parser)
    build_command(parser)
    # run it..
    args = parser.parse_args()
    # validate..
    if args.help_checkers_verbose:
        print_checkers(get_checkers(args.clang, args.plugins))
        parser.exit()
    elif args.help_checkers:
        print_active_checkers(get_checkers(args.clang, args.plugins))
        parser.exit()
    if not args.build:
        parser.error('missing build command')
    # return it..
    return args


def setup_environment(args, destination, wrapper_dir):
    """ Sets up the environment for the build command. """

    environment = dict(os.environ)
    environment.update({
        'CC': os.path.join(wrapper_dir, 'analyze-cc'),
        'CXX': os.path.join(wrapper_dir, 'analyze-cxx'),
        'BUILD_ANALYZE_CC': args.cc,
        'BUILD_ANALYZE_CXX': args.cxx,
        'BUILD_ANALYZE_CLANG': args.clang,
        'BUILD_ANALYZE_VERBOSE': 'DEBUG' if args.verbose > 2 else 'WARNING',
        'BUILD_ANALYZE_REPORT_DIR': destination,
        'BUILD_ANALYZE_REPORT_FORMAT': args.output_format,
        'BUILD_ANALYZE_REPORT_FAILURES': 'yes' if args.report_failures else '',
        'BUILD_ANALYZE_PARAMETERS': ' '.join(analyzer_params(args))
    })
    return environment


def wrapper(cplusplus):
    """ This method implements basic compiler wrapper functionality. """

    # initialize wrapper logging
    logging.basicConfig(format='analyze: %(levelname)s: %(message)s',
                        level=os.getenv('BUILD_ANALYZE_VERBOSE', 'INFO'))
    # execute with real compiler
    compiler = os.getenv('BUILD_ANALYZE_CXX', 'c++') if cplusplus \
        else os.getenv('BUILD_ANALYZE_CC', 'cc')
    compilation = [compiler] + sys.argv[1:]
    logging.info('execute compiler: %s', compilation)
    result = subprocess.call(compilation)
    try:
        # collect the needed parameters from environment, crash when missing
        consts = {
            'clang': os.getenv('BUILD_ANALYZE_CLANG'),
            'output_dir': os.getenv('BUILD_ANALYZE_REPORT_DIR'),
            'output_format': os.getenv('BUILD_ANALYZE_REPORT_FORMAT'),
            'report_failures': os.getenv('BUILD_ANALYZE_REPORT_FAILURES'),
            'direct_args': os.getenv('BUILD_ANALYZE_PARAMETERS',
                                     '').split(' '),
            'directory': os.getcwd(),
        }
        # get relevant parameters from command line arguments
        args = classify_parameters(sys.argv)
        filenames = args.pop('files', [])
        for filename in (name for name in filenames if is_source_file(name)):
            parameters = dict(args, file=filename, **consts)
            logging.debug('analyzer parameters %s', parameters)
            current = action_check(parameters)
            # display error message from the static analyzer
            if current is not None:
                for line in current['error_output']:
                    logging.info(line.rstrip())
    except Exception:
        logging.exception("run analyzer inside compiler wrapper failed.")
    # return compiler exit code
    return result
