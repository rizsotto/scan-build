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
import tempfile
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
