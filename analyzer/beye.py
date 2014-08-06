# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.


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

    import multiprocessing
    multiprocessing.freeze_support()

    args = parse_command_line()
    logging.basicConfig(format='%(message)s', level=args.log_level)

    out_dir = create_out_directory(args.output)
    if run_analyzer(args, out_dir) and found_bugs(out_dir):
        generate_report(out_dir)
        logging.info('output directory: {}'.format(result))
    else:
        cleanup_out_directory(out_dir)


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
                        default='INFO',
                        help="Choose a log level from DEBUG, INFO (default),\
                              WARNING or ERROR")
    return parser.parse_args()


def found_bugs(out_dir):
    return True


def generate_report(out_dir):
    pass


def run_analyzer(opts, out_dir):
    with open(opts.input, 'r') as fd:
        if opts.sequential:
            for c in json.load(fd):
                analyze(c, opts, out_dir)
        else:
            pool = multiprocessing.Pool()
            for c in json.load(fd):
                pool.apply_async(func=analyze, args=(c, opts, out_dir))
            pool.close()
            pool.join()

    return True


def analyze(task, opts, out_dir):
    import analyzer.driver
    task['html_dir'] = out_dir
    task['output_format'] = 'html'
    cmds = shlex.split(task['command'])
    task['command'] = cmds
    return analyzer.driver.run(**task)
