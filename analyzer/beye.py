# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import multiprocessing
import subprocess
import json
import itertools
import re
import os
import os.path
import shutil
import glob
from xml.sax.saxutils import escape
from analyzer.decorators import trace, require
from analyzer.driver import (
    run, filter_dict, get_clang_arguments, get_clang_version)


def main():
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
            return 5

    def needs_report_file(opts):
        output_format = opts.get('output_format')
        return 'html' == output_format or 'plist-html' == output_format

    args = parse_command_line()

    logging.getLogger().setLevel(from_number_to_level(args['verbose']))
    logging.debug(args)

    with ReportDirectory(args['output'], args['keep_empty']) as out_dir:
        run_analyzer(args, out_dir)
        number_of_bugs = generate_report(args, out_dir)\
            if needs_report_file(args) else 0
        # TODO get result from bear if --status-bugs were not requested
        return number_of_bugs if 'status_bugs' in args else 0


class ReportDirectory(object):

    def __init__(self, hint, keep):
        self.name = ReportDirectory._create(hint)
        self.keep = keep

    def __enter__(self):
        return self.name

    @trace
    def __exit__(self, type, value, traceback):
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
        if hint != '/tmp':
            import os
            try:
                os.mkdir(hint)
                return hint
            except OSError as ex:
                raise
        else:
            import tempfile
            return tempfile.mkdtemp(prefix='beye-', suffix='.out')


@trace
def parse_command_line():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(prog='beye',
                            formatter_class=ArgumentDefaultsHelpFormatter)
    group1 = parser.add_argument_group('options')
    group1.add_argument(
        '--analyze-headers',
        action='store_true',
        help='Also analyze functions in #included files. By default,\
              such functions are skipped unless they are called by\
              functions within the main source file.')
    group1.add_argument(
        '--output', '-o',
        metavar='<path>',
        default='/tmp',
        help='Specifies the output directory for analyzer reports.\
              Subdirectories will be created as needed to represent separate\
              "runs" of the analyzer.')
    group1.add_argument(
        '--html-title',
        metavar='<title>',
        help='Specify the title used on generated HTML pages.\
              If not specified, a default title will be used.')
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
        '--status-bugs',
        action='store_true',
        help='By default, the exit status of ‘beye’ is the same as the\
              executed build command. Specifying this option causes the exit\
              status of ‘beye’ to be 1 if it found potential bugs and 0\
              otherwise.')
    group1.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help="Enable verbose output from ‘beye’. A second and third '-v'\
              increases verbosity.")
    # TODO: implement '-view '

    group2 = parser.add_argument_group('advanced options')
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
        '--input',
        metavar='<file>',
        default="compile_commands.json",
        help="The JSON compilation database.")
    group2.add_argument(
        '--sequential',
        action='store_true',
        help="Execute analyzer sequentialy.")

    group3 = parser.add_argument_group('controlling checkers')
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

    return parser.parse_args().__dict__


@trace
@require(['input'])
def run_analyzer(args, out_dir):
    def common_params(opts):
        def uname():
            return subprocess.check_output(['uname', '-a']).decode('ascii')

        return filter_dict(
            opts,
            frozenset([
                'output',
                'html_title',
                'keep_empty',
                'status_bugs',
                'input',
                'sequential']),
            {'html_dir': out_dir,
             'uname': uname()})

    def wrap(iterable, const):
        for current in iterable:
            current.update(const)
            yield current

    with open(args['input'], 'r') as fd:
        pool = multiprocessing.Pool(1 if 'sequential' in args else None)
        for current in pool.imap_unordered(
                run, wrap(json.load(fd), common_params(args))):
            if current is not None and 'analyzer' in current:
                for line in current['analyzer']['error_output']:
                    logging.info(line.rstrip())
        pool.close()
        pool.join()


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


@trace
def generate_report(args, out_dir):
    pool = multiprocessing.Pool(1 if 'sequential' in args else None)
    result = 0
    with bug_fragment(
            pool.imap_unordered(scan_bug,
                                glob.iglob(os.path.join(out_dir,
                                                        '*.html'))),
            out_dir) as bugs:
        with crash_fragment(
                pool.imap_unordered(scan_crash,
                                    glob.iglob(os.path.join(out_dir,
                                                            'failures',
                                                            '*.info.txt'))),
                out_dir) as crashes:
            result = bugs.count + crashes.count
            if result > 0:
                assembly_report(args, out_dir, bugs, crashes)
                copy_resource_files(out_dir)
    pool.close()
    pool.join()
    return result


@trace
def scan_bug(result):
    """ Parse out the bug information from HTML output. """
    def classname(bug):
        def smash(key):
            return bug.get(key, '').lower().replace(' ', '_')
        return 'bt_' + smash('bug_category') + '_' + smash('bug_type')

    def safe_value(container, key, encode):
        if key in container:
            value = encode(container[key])
            container.update({key: value})

    patterns = [
        re.compile('<!-- BUGTYPE (?P<bug_type>.*) -->$'),
        re.compile('<!-- BUGFILE (?P<bug_file>.*) -->$'),
        re.compile('<!-- BUGPATHLENGTH (?P<bug_path_length>.*) -->$'),
        re.compile('<!-- BUGLINE (?P<bug_line>.*) -->$'),
        re.compile('<!-- BUGCATEGORY (?P<bug_category>.*) -->$'),
        re.compile('<!-- BUGDESC (?P<bug_description>.*) -->$'),
        re.compile('<!-- FUNCTIONNAME (?P<bug_function>.*) -->$')]
    endsign = re.compile('<!-- BUGMETAEND -->')

    bug_info = dict()
    with open(result) as handler:
        for line in handler.readlines():
            # do not read the file further
            if endsign.match(line):
                break
            # search for the right lines
            for regex in patterns:
                match = regex.match(line.strip())
                if match:
                    bug_info.update(match.groupdict())

    # fix some default values
    bug_info['bug_category'] = bug_info.get('bug_category', 'Other')
    bug_info['bug_path_length'] = int(bug_info.get('bug_path_length', 1))
    bug_info['bug_line'] = int(bug_info.get('bug_line', 0))
    bug_info['report_file'] = result
    bug_info['bug_type_class'] = classname(bug_info)
    safe_value(bug_info, 'bug_category', escape)
    safe_value(bug_info, 'bug_type', escape)
    safe_value(bug_info, 'bug_type_class', escape)

    return bug_info


@trace
def scan_crash(filename):
    match = re.match('(.*)\.info\.txt', filename)
    name = match.group(1) if match else None
    with open(filename) as handler:
        lines = handler.readlines()
        return {'source': escape(lines[0].rstrip()),
                'problem': escape(lines[1].rstrip()),
                'preproc': escape(name),
                'stderr': escape(name + '.stderr.txt')},


class ReportFragment(object):
    """ Represents a report fragment on the disk. The only usage at report
        generation, when multiple fragments are combined together. """

    def __init__(self, filename, count):
        self.filename = filename
        self.count = count

    def __enter__(self):
        return self

    @trace
    def __exit__(self, exc_type, exc_value, traceback):
        os.remove(self.filename)

    @trace
    def write(self, output_handle):
        if self.count:
            with open(self.filename, 'r') as input_handle:
                for line in input_handle:
                    output_handle.write(line)


@trace
def crash_fragment(iterator, out_dir):
    name = os.path.join(out_dir, 'crashes.html.fragment')
    count = 0
    with open(name, 'w') as handle:
        indent = 4
        handle.write(reindent("""
        |<h2>Analyzer Failures</h2>
        |<p>The analyzer had problems processing the following files:</p>
        |<table>
        |  <thead>
        |    <tr>
        |      <td>Problem</td>
        |      <td>Source File</td>
        |      <td>Preprocessed File</td>
        |      <td>STDERR Output</td>
        |    </tr>
        |  </thead>
        |  <tbody>""", indent))
        for current in iterator:
            count += 1
            handle.write(reindent("""
        |    <tr>
        |      <td>{problem}</td>
        |      <td>{source}</td>
        |      <td><a href="{preproc}">preprocessor output</a></td>
        |      <td><a href="{stderr}">analyzer std err</a></td>
        |    </tr>""", indent).format(**current))
        handle.write(reindent("""
        |  </tbody>
        |</table>""", indent))
    return ReportFragment(name, count)


@trace
def bug_fragment(iterator, out_dir):
    def hash_bug(bug):
        return str(bug['bug_line']) + ':' +\
            str(bug['bug_path_length']) + ':' +\
            bug['bug_file'][::-1]

    def update_counters(counters, bug):
        bug_category = bug['bug_category']
        current_category = counters.get(bug_category, dict())
        bug_type = bug['bug_type']
        current_type = current_category.get(bug_type, {
            'bug_type': bug_type,
            'bug_type_class': bug['bug_type_class'],
            'bug_count': 0})
        current_type.update({'bug_count': current_type['bug_count'] + 1})
        current_category.update({bug_type: current_type})
        counters.update({bug_category: current_category})

    name = os.path.join(out_dir, 'bugs.html.fragment')
    uniques = set()
    counters = dict()
    with open(name, 'w') as handle:
        indent = 4
        handle.write(reindent("""
        |<h2>Reports</h2>
        |<table class="sortable" style="table-layout:automatic">
        |  <thead>
        |    <tr>
        |      <td>Bug Group</td>
        |      <td class="sorttable_sorted">
        |        Bug Type
        |        <span id="sorttable_sortfwdind">&nbsp;&#x25BE;</span>
        |      </td>
        |      <td>File</td>
        |      <td class="Q">Line</td>
        |      <td class="Q">Path Length</td>
        |      <td class="sorttable_nosort"></td>
        |    </tr>
        |  </thead>
        |  <tbody>""", indent))
        for current in iterator:
            hash = hash_bug(current)
            if hash not in uniques:
                uniques.add(hash)
                update_counters(counters, current)
                handle.write(reindent("""
        |    <tr class={bug_type_class}>
        |      <td class="DESC">{bug_category}</td>
        |      <td class="DESC">{bug_type}</td>
        |      <td>{bug_file}</td>
        |      <td class="Q">{bug_line}</td>
        |      <td class="Q">{bug_path_length}</td>
        |      <td><a href="{report_file}#EndPath">View Report</a></td>
        |    </tr>""", indent).format(**current))
        handle.write(reindent("""
        |  </tbody>
        |</table>""", indent))
    with ReportFragment(name, len(uniques)) as bugs:
        return summary_fragment(counters, out_dir, bugs)\
            if bugs.count else bugs


@trace
def summary_fragment(counters, out_dir, tail_fragment):
    name = os.path.join(out_dir, 'summary.html.fragment')
    with open(name, 'w') as handle:
        indent = 4
        handle.write(reindent("""
        |<h2>Bug Summary</h2>
        |<table>
        |  <thead>
        |    <tr>
        |      <td>Bug Type</td>
        |      <td>Quantity</td>
        |      <td class="sorttable_nosort">Display?</td>
        |    </tr>
        |  </thead>
        |  <tbody>""", indent))
        handle.write(reindent("""
        |    <tr style="font-weight:bold">
        |      <td class="SUMM_DESC">All Bugs</td>
        |      <td class="Q">{0}</td>
        |      <td>
        |        <center>
        |          <input checked type="checkbox" id="AllBugsCheck"
        |                 onClick="CopyCheckedStateToCheckButtons(this);"/>
        |        </center>
        |      </td>
        |    </tr>""", indent).format(tail_fragment.count))
        for category, types in counters.items():
            handle.write(reindent("""
        |    <tr>
        |      <th>{0}</th><th colspan=2></th>
        |    </tr>""", indent).format(category))
            for bug_type in types.values():
                handle.write(reindent("""
        |    <tr>
        |      <td class="SUMM_DESC">{bug_type}</td>
        |      <td class="Q">{bug_count}</td>
        |      <td>
        |        <center>
        |          <input checked type="checkbox"
        |                 onClick="ToggleDisplay(this,'{bug_type_class}');"/>
        |        </center>
        |      </td>
        |    </tr>""", indent).format(**bug_type))
        handle.write(reindent("""
        |  </tbody>
        |</table>""", indent))
        tail_fragment.write(handle)
    return ReportFragment(name, tail_fragment.count)


@trace
@require(['clang'])
def assembly_report(opts, out_dir, *fragments):
    import getpass
    import socket
    import sys
    import datetime

    if 'html_title' not in opts or opts['html_title'] is None:
        opts['html_title'] = os.getcwd() + ' - analyzer results'

    output = os.path.join(out_dir, 'index.html')
    with open(output, 'w') as handle:
        handle.write(reindent("""
        |<!DOCTYPE html>
        |<html>
        |  <head>
        |    <title>{html_title}</title>
        |    <link type="text/css" rel="stylesheet" href="scanview.css"/>
        |    <script type='text/javascript' src="sorttable.js"></script>
        |    <script type='text/javascript' src='selectable.js'></script>
        |  </head>
        |  <body>
        |    <h1>{html_title}</h1>
        |    <table>
        |      <tr><th>User:</th><td>{user_name}@{host_name}</td></tr>
        |      <tr><th>Working Directory:</th><td>{current_dir}</td></tr>
        |      <tr><th>Command Line:</th><td>{cmd_args}</td></tr>
        |      <tr><th>Clang Version:</th><td>{clang_version}</td></tr>
        |      <tr><th>Date:</th><td>{date}</td></tr>
        |    </table>""", 0).format(
            html_title=opts['html_title'],
            user_name=getpass.getuser(),
            host_name=socket.gethostname(),
            current_dir=os.getcwd(),
            cmd_args=' '.join(sys.argv),
            clang_version=get_clang_version(opts['clang']),
            date=datetime.datetime.today().strftime('%c')))
        for fragment in fragments:
            fragment.write(handle)
        handle.write(reindent("""
        |  </body>
        |</html>""", 0))


@trace
def copy_resource_files(out_dir):
    this_dir, _ = os.path.split(__file__)
    resources_dir = os.path.join(this_dir, 'resources')
    shutil.copy(os.path.join(resources_dir, 'scanview.css'), out_dir)
    shutil.copy(os.path.join(resources_dir, 'sorttable.js'), out_dir)
    shutil.copy(os.path.join(resources_dir, 'selectable.js'), out_dir)


def reindent(text, indent):
    result = ''
    for line in text.splitlines():
        if len(line.strip()):
            result += ' ' * indent + line.split('|')[1] + os.linesep
    return result
