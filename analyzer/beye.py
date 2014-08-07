# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import shlex
import logging
import multiprocessing
import json
import itertools
from analyzer.decorators import trace, require
from analyzer.driver import run, get_clang_arguments, check_output, filter_dict


def main():
    multiprocessing.freeze_support()
    logging.basicConfig(format='%(message)s')

    def cleanup_out_directory(dir_name):
        import shutils
        shutil.rmtree(dir_name)

    def create_out_directory(hint):
        if (hint):
            import os
            try:
                os.mkdir(hint)
                return hint
            except OSError as ex:
                raise
        else:
            import tempfile
            return tempfile.mkdtemp(prefix='beye-', suffix='.out')

    args = parse_command_line()

    logging.getLogger().setLevel(args.log_level)

    out_dir = create_out_directory(args.output)
    if run_analyzer(args, out_dir) and found_bugs(out_dir):
        generate_report(out_dir)
        logging.warning('output directory: {0}'.format(out_dir))
    else:
        cleanup_out_directory(out_dir)
        logging.warning('no bugs were found')


@trace
def parse_command_line():
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--output",
                        metavar='DIR',
                        help="Specify output directory\
                              (default generated)")
    parser.add_argument("--input",
                        metavar='FILE',
                        default="compile_commands.json",
                        help="The JSON compilation database\
                              (default compile_commands.json)")
    parser.add_argument("--sequential",
                        action='store_true',
                        help="execute analyzer sequentialy (default false)")
    parser.add_argument('--log-level',
                        metavar='LEVEL',
                        choices='DEBUG INFO WARNING ERROR'.split(),
                        default='WARNING',
                        help="Choose a log level from DEBUG, INFO,\
                              WARNING (default) or ERROR")
    return parser.parse_args()


@trace
def found_bugs(out_dir):
    return True


@trace
def generate_report(out_dir):
    pass


@trace
def run_analyzer(args, out_dir):
    def set_common_params(opts):
        return filter_dict(
            opts,
            frozenset(['output', 'input', 'sequential', 'log_level']),
            {'verbose': logging.getLogger().isEnabledFor(logging.INFO),
             'html_dir': out_dir,
             'output_format': opts.get('output_format', 'html'),
             'uname': check_output(['uname', '-a']).decode('ascii'),
             'clang': 'clang'})

    const = set_common_params(args.__dict__)
    with open(args.input, 'r') as fd:
        pool = multiprocessing.Pool(1 if args.sequential else None)
        for c in json.load(fd):
            c.update(const)
            c.update(command=shlex.split(c['command']))
            pool.apply_async(func=run, args=(c,))
        pool.close()
        pool.join()

    return True


@trace
def get_default_checkers(clang):
    """ To get the default plugins we execute Clang to print how this
    comilation would be called. For input file we specify stdin. And
    pass only language information. """
    def checkers(language):
        pattern = re.compile('^-analyzer-checker=(.*)$')
        cmd = [clang, '--analyze', '-x', language, '-']
        return [pattern.match(arg).group(1)
                for arg
                in get_clang_arguments('.', cmd)
                if pattern.match(arg)]
    return set(itertools.chain.from_iterable(
               [checkers(language)
                for language
                in ['c', 'c++', 'objective-c', 'objective-c++']]))
