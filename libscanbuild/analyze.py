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

import re
import os
import os.path
import json
import logging
import multiprocessing
from libscanbuild import command_entry_point, wrapper_environment, \
    wrapper_entry_point, run_build
from libscanbuild.runner import run, logging_analyzer_output
from libscanbuild.intercept import capture
from libscanbuild.report import report_directory, document
from libscanbuild.compilation import split_command
from libscanbuild.arguments import scan, analyze

__all__ = ['scan_build', 'analyze_build', 'analyze_build_wrapper']

COMPILER_WRAPPER_CC = 'analyze-cc'
COMPILER_WRAPPER_CXX = 'analyze-c++'
ENVIRONMENT_KEY = 'ANALYZE_BUILD'


@command_entry_point
def scan_build():

    args = scan()
    with report_directory(args.output, args.keep_empty) as target_dir:
        # target_dir is the new output
        args.output = target_dir
        # run against a build command. there are cases, when analyzer run
        # is not required. but we need to set up everything for the
        # wrappers, because 'configure' needs to capture the CC/CXX values
        # for the Makefile.
        if args.intercept_first:
            # run build command with intercept module
            exit_code = capture(args)
            if need_analyzer(args.build):
                # run the analyzer against the captured commands
                run_analyzer(args)
        else:
            # run build command and analyzer with compiler wrappers
            environment = setup_environment(args)
            exit_code = run_build(args.build, env=environment)
        # cover report generation and bug counting
        number_of_bugs = document(args, target_dir)
        # do cleanup temporary files
        if args.intercept_first:
            os.unlink(args.cdb)
        # set exit status as it was requested
        return number_of_bugs if args.status_bugs else exit_code


@command_entry_point
def analyze_build():

    args = analyze()
    with report_directory(args.output, args.keep_empty) as target_dir:
        # target_dir is the new output
        args.output = target_dir
        # run the analyzer against a compilation db
        run_analyzer(args)
        # cover report generation and bug counting
        number_of_bugs = document(args, target_dir)
        # set exit status as it was requested
        return number_of_bugs if args.status_bugs else 0


def need_analyzer(args):
    """ Check the intent of the build command.

    When static analyzer run against project configure step, it should be
    silent and no need to run the analyzer or generate report.

    To run `scan-build` against the configure step might be necessary,
    when compiler wrappers are used. That's the moment when build setup
    check the compiler and capture the location for the build process. """

    return len(args) and not re.search('configure|autogen', args[0])


def analyze_parameters(args):
    """ Mapping between the command line parameters and the analyzer run
    method. The run method works with a plain dictionary, while the command
    line parameters are in a named tuple.
    The keys are very similar, and some values are preprocessed. """

    def prefix_with(constant, pieces):
        """ From a sequence create another sequence where every second element
        is from the original sequence and the odd elements are the prefix.

        eg.: prefix_with(0, [1,2,3]) creates [0, 1, 0, 2, 0, 3] """

        return [elem for piece in pieces for elem in [constant, piece]]

    def direct_args(args):
        """ A group of command line arguments can mapped to command
        line arguments of the analyzer. """

        result = []

        if args.store_model:
            result.append('-analyzer-store={0}'.format(args.store_model))
        if args.constraints_model:
            result.append('-analyzer-constraints={0}'.format(
                args.constraints_model))
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
        if args.verbose >= 4:
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

    return {
        'clang': args.clang,
        'output_dir': args.output,
        'output_format': args.output_format,
        'output_failures': args.output_failures,
        'direct_args': direct_args(args),
        'force_debug': args.force_debug,
        'excludes': args.excludes
    }


def run_analyzer(args):
    """ Runs the analyzer against the given compilation database. """

    logging.debug('run analyzer against compilation database')
    with open(args.cdb, 'r') as handle:
        consts = analyze_parameters(args)
        entries = (dict(cmd, **consts) for cmd in json.load(handle))
        # when verbose output requested execute sequentially
        pool = multiprocessing.Pool(1 if args.verbose > 2 else None)
        for current in pool.imap_unordered(run, entries):
            logging_analyzer_output(current)
        pool.close()
        pool.join()


def setup_environment(args):
    """ Set up environment for build command to interpose compiler wrapper. """

    environment = dict(os.environ)
    # to run compiler wrappers
    environment.update(
        wrapper_environment(
            c_wrapper=COMPILER_WRAPPER_CC,
            cxx_wrapper=COMPILER_WRAPPER_CXX,
            c_compiler=args.cc,
            cxx_compiler=args.cxx,
            verbose=args.verbose))
    # pass the relevant parameters to run the analyzer with condition.
    # the presence of the environment value will control the run.
    if need_analyzer(args.build):
        environment.update({
            ENVIRONMENT_KEY: json.dumps(analyze_parameters(args))
        })
    return environment


@command_entry_point
@wrapper_entry_point
def analyze_build_wrapper(**kwargs):
    """ Entry point for `analyze-cc` and `analyze-c++` compiler wrappers. """

    # don't run analyzer when compilation fails. or when it's not requested.
    if kwargs['result'] or not os.getenv(ENVIRONMENT_KEY):
        return
    # don't run analyzer when the command is not a compilation
    # (can be preprocessing or a linking only execution of the compiler)
    compilation = split_command(kwargs['command'])
    if compilation is None:
        return
    # collect the needed parameters from environment
    parameters = json.loads(os.environ[ENVIRONMENT_KEY])
    parameters.update({
        'directory': os.getcwd(),
        'command': [kwargs['compiler'], '-c'] + compilation.flags
    })
    # call static analyzer against the compilation
    for source in compilation.files:
        current = run(dict(parameters, file=source))
        # display error message from the static analyzer
        logging_analyzer_output(current)
