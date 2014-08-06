# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import analyzer.driver
import shlex
import logging
import multiprocessing
import json


def run():
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

    multiprocessing.freeze_support()

    args = parse_command_line()
    logging.basicConfig(format='%(message)s', level=args.log_level)

    out_dir = create_out_directory(args.output)
    if run_analyzer(args, out_dir) and found_bugs(out_dir):
        generate_report(out_dir)
        logging.warning('output directory: {0}'.format(out_dir))
    else:
        cleanup_out_directory(out_dir)
        logging.warning('no bugs were found')


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


def found_bugs(out_dir):
    return True


def generate_report(out_dir):
    pass


def run_analyzer(args, out_dir):
    def set_common_params(opts):
        output = analyzer.driver.check_output
        return analyzer.driver.filter_dict(
            opts,
            frozenset(['output', 'input', 'sequential', 'log_level']),
            {'verbose': True,
             'html_dir': out_dir,
             'output_format': opts.get('output_format', 'html'),
             'uname': output(['uname', '-a']).decode('ascii'),
             'clang': 'clang'})

    const = set_common_params(args.__dict__)
    with open(args.input, 'r') as fd:
        pool = multiprocessing.Pool(1 if args.sequential else None)
        for c in json.load(fd):
            c.update(const)
            c.update(command=shlex.split(c['command']))
            pool.apply_async(func=analyzer.driver.run, args=(c,))
        pool.close()
        pool.join()

    return True
