# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

""" This module is responsible to run the analyzer commands. """


import subprocess
import logging
import os
import os.path
import shlex
import tempfile
import json
from analyzer.command import classify_parameters, Action
from analyzer.decorators import trace, require
from analyzer.clang import get_arguments, get_version


@trace
def run(opts):
    """ Execute given analyzer command.

    Other modules prepared the command line arguments for analyzer execution.
    The missing parameter related to the output of the analyzer. This method
    assemble and execute the final analyzer command. """

    try:
        return set_analyzer_output(opts)
    except Exception as exception:
        logging.error(str(exception))
        return None


@trace
def generate_commands(args):
    """ From compilation database it creates analyzer commands. """

    def extend(opts, direct_args):
        """ Take a compilation database entry and extend it with classified
        compiler parameters and direct arguments from command line. """

        opts.update(classify_parameters(shlex.split(opts['command'])))
        opts.update({'direct_args': direct_args})
        return opts

    direct_args = _analyzer_params(args)
    with open(args.cdb, 'r') as handle:
        generator = (extend(cmd, direct_args) for cmd in json.load(handle))
        return _create_commands(
            _language_check(_arch_check(_action_check(generator))))


@trace
def _analyzer_params(args):
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
    if args.ubiviz:
        result.append('-analyzer-viz-egraph-ubigraph')

    return prefix_with('-Xclang', result)


@trace
def _create_commands(iterator):
    """ Create command to run analyzer or failure report generation.

    If output is passed it returns failure report command.
    If it's not given it returns the analyzer command. """

    for current in iterator:
        common = []
        if 'arch' in current:
            common.extend(['-arch', current['arch']])
        if 'compile_options' in current:
            common.extend(current['compile_options'])
        common.extend(['-x', current['language']])
        common.append(current['file'])

        yield {
            'directory': current['directory'],
            'file': current['file'],
            'language': current['language'],
            'analyze': ['--analyze'] + current['direct_args'] + common,
            'report': ['-fsyntax-only', '-E'] + common}


@trace
def _language_check(iterator):
    """ Find out the language from command line parameters or file name
    extension. The decision also influenced by the compiler invocation. """

    def from_filename(name, cplusplus_compiler):
        """ Return the language from fille name extension. """

        mapping = {
            '.c': 'c++' if cplusplus_compiler else 'c',
            '.cp': 'c++',
            '.cpp': 'c++',
            '.cxx': 'c++',
            '.txx': 'c++',
            '.cc': 'c++',
            '.C': 'c++',
            '.ii': 'c++-cpp-output',
            '.i': 'c++-cpp-output' if cplusplus_compiler else 'c-cpp-output',
            '.m': 'objective-c',
            '.mi': 'objective-c-cpp-output',
            '.mm': 'objective-c++',
            '.mii': 'objective-c++-cpp-output'
        }
        (_, extension) = os.path.splitext(os.path.basename(name))
        return mapping.get(extension)

    accepteds = {'c', 'c++', 'objective-c', 'objective-c++',
                 'c-cpp-output', 'c++-cpp-output', 'objective-c-cpp-output'}

    key = 'language'
    for current in iterator:
        language = current[key] if key in current else \
            from_filename(current['file'], current.get('cxx', False))
        if language is None:
            logging.debug('skip analysis, language not known')
        elif language not in accepteds:
            logging.debug('skip analysis, language not supported')
        else:
            logging.debug('analysis, language: {0}'.format(language))
            current.update({key: language})
            yield current


@trace
def _arch_check(iterator):
    """ Do run analyzer through one of the given architectures. """

    disableds = {'ppc', 'ppc64'}

    key = 'archs_seen'
    for current in iterator:
        if key in current:
            # filter out disabled architectures and -arch switches
            archs = [a for a in current[key]
                     if '-arch' != a and a not in disableds]

            if not archs:
                logging.debug('skip analysis, found not supported arch')
            else:
                # There should be only one arch given (or the same multiple
                # times). If there are multiple arch are given and are not
                # the same, those should not change the pre-processing step.
                # But that's the only pass we have before run the analyzer.
                arch = archs.pop()
                logging.debug('analysis, on arch: {0}'.format(arch))

                current.update({'arch': arch})
                del current[key]
                yield current
        else:
            logging.debug('analysis, on default arch')
            yield current


@trace
def _action_check(iterator):
    """ Continue analysis only if it compilation or link. """

    for current in iterator:
        if current['action'] <= Action.Compile:
            yield current
        else:
            logging.debug('skip analysis, not compilation nor link')


@trace
@require(['report', 'directory',
          'clang', 'out_dir', 'language',
          'file', 'error_type', 'error_output', 'exit_code'])
def report_failure(opts):
    """ Create report when analyzer failed.

    The major report is the preprocessor output. The output filename generated
    randomly. The compiler output also captured into '.stderr.txt' file. And
    some more execution context also saved into '.info.txt' file.
    """
    def extension(opts):
        """ Generate preprocessor file extension. """
        mapping = {
            'objective-c++': '.mii',
            'objective-c': '.mi',
            'c++': '.ii'
        }
        return mapping.get(opts['language'], '.i')

    def destination(opts):
        """ Creates failures directory if not exits yet. """
        name = os.path.join(opts['out_dir'], 'failures')
        if not os.path.isdir(name):
            os.makedirs(name)
        return name

    error = opts['error_type']
    (handle, name) = tempfile.mkstemp(suffix=extension(opts),
                                      prefix='clang_' + error + '_',
                                      dir=destination(opts))
    os.close(handle)
    cwd = opts['directory']
    cmd = get_arguments(cwd, [opts['clang']] + opts['report'] + ['-o', name])
    logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
    subprocess.call(cmd, cwd=cwd)

    with open(name + '.info.txt', 'w') as handle:
        handle.write(opts['file'] + os.linesep)
        handle.write(error.title().replace('_', ' ') + os.linesep)
        handle.write(' '.join(cmd) + os.linesep)
        handle.write(' '.join(os.uname()) + os.linesep)
        handle.write(get_version(cmd[0]))
        handle.close()

    with open(name + '.stderr.txt', 'w') as handle:
        handle.writelines(opts['error_output'])
        handle.close()

    return {'error_output': opts['error_output'],
            'exit_code': opts['exit_code']}


@trace
@require(['clang', 'analyze', 'directory', 'output'])
def run_analyzer(opts, continuation=report_failure):
    """ From the state parameter it assembles the analysis command line and
    executes it. Capture the output of the analysis and returns with it. If
    failure reports are requested, it calls the continuation to generate it.
    """
    cwd = opts['directory']
    cmd = [opts['clang']] + opts['analyze'] + opts['output']
    logging.debug('exec command in {0}: {1}'.format(cwd, ' '.join(cmd)))
    child = subprocess.Popen(cmd,
                             cwd=cwd,
                             universal_newlines=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
    output = child.stdout.readlines()
    child.stdout.close()
    # do report details if it were asked
    child.wait()
    if opts.get('report_failures', False) and child.returncode:
        error_type = 'crash' if child.returncode & 127 else 'other_error'
        opts.update(
            {'error_type': error_type,
             'error_output': output,
             'exit_code': child.returncode})
        return continuation(opts)
    return {'error_output': output,
            'exit_code': child.returncode}


@trace
@require(['out_dir'])
def set_analyzer_output(opts, continuation=run_analyzer):
    """ Create output file if was requested.

    This plays a role only if .plist files are requested. """
    def needs_output_file():
        output_format = opts.get('output_format')
        return 'plist' == output_format or 'plist-html' == output_format

    if needs_output_file():
        with tempfile.NamedTemporaryFile(prefix='report-',
                                         suffix='.plist',
                                         delete='out_dir' not in opts,
                                         dir=opts.get('out_dir')) as output:
            opts.update({'output': ['-o', output.name]})
            return continuation(opts)
    else:
        opts.update({'output': ['-o', opts['out_dir']]})
        return continuation(opts)
