# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import multiprocessing
import itertools
import re
import os
import os.path
import shutil
import glob
from analyzer.decorators import trace
from analyzer.driver import filter_dict, get_clang_version


@trace
def generate_report(args, out_dir):
    # TODO: don't do any of these if output format was not html
    pool = multiprocessing.Pool(1 if 'sequential' in args else None)
    (bugs, count1) = bug_fragment(
        pool.imap_unordered(scan_bug,
                            glob.iglob(os.path.join(out_dir,
                                                    '*.html'))),
        out_dir)
    (crashes, count2) = crash_fragment(
        pool.imap_unordered(scan_crash,
                            glob.iglob(os.path.join(out_dir,
                                                    'failures',
                                                    '*.info.txt'))),
        out_dir)
    pool.close()
    pool.join()
    if count1 + count2 > 0:
        assembly_report(args, out_dir, bugs, crashes)
    os.remove(bugs)
    os.remove(crashes)
    return count1 + count2


@trace
def scan_bug(result):
    """ Parse out the bug information from HTML output. """
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

    return bug_info


@trace
def scan_crash(filename):
    match = re.match('(.*)\.info\.txt', filename)
    name = match.group(1) if match else None
    with open(filename) as handler:
        lines = handler.readlines()
        return {'source': lines[0].rstrip(),
                'problem': lines[1].rstrip(),
                'preproc': name,
                'stderr': name + '.stderr.txt'},


@trace
def crash_fragment(iterator, out_dir):
    name = os.path.join(out_dir, 'crashes.html.fragment')
    count = 0
    with open(name, 'w') as handle:
        indent = 4
        handle.write(reindent("""
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
    return (name, count)


@trace
def bug_fragment(iterator, out_dir):
    def hash_bug(bug):
        return str(bug['bug_line']) + ':' +\
            str(bug['bug_path_length']) + ':' +\
            bug['bug_file'][::-1]

    def update_counters(counters, bug):
        category = bug['bug_category']
        current = counters.get(category, 0)
        counters.update({category: current + 1})

    name = os.path.join(out_dir, 'bugs.html.fragment')
    uniques = set()
    counters = dict()
    with open(name, 'w') as handle:
        indent = 4
        handle.write(reindent("""
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
        |    <tr>
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
    return (name, len(uniques))


@trace
def assembly_report(opts, out_dir, bug_fragment, crash_fragment):
    import getpass
    import socket
    import sys
    import datetime

    def from_file(output_handle, file_name):
        with open(file_name, 'r') as input_handle:
            for line in input_handle:
                output_handle.write(line)

    def default_title():
        return os.getcwd() + ' - analyzer results'

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
        |{version_section}
        |    </table>""", 0).format(
            html_title=opts.get('html_title', default_title()),
            user_name=getpass.getuser(),
            host_name=socket.gethostname(),
            current_dir=os.getcwd(),
            cmd_args=' '.join(sys.argv),
            clang_version=get_clang_version(opts['clang']),
            date=datetime.datetime.today().strftime('%c'),
            version_section=''))
        from_file(handle, bug_fragment)
        from_file(handle, crash_fragment)
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
