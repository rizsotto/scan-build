# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import logging
import itertools
import re
import glob
import os
import os.path
import shutil
import multiprocessing
from analyzer.decorators import trace
from analyzer.driver import filter_dict, get_clang_version


@trace
def generate_report(args, out_dir):
    """ Generate the index.html """
    def consume(result, new):
        category = new['bug_category']
        current = result.get(category, [])
        current.append(new)
        result.update({category: current})

    @trace
    def copy_resource_files():
        this_dir, _ = os.path.split(__file__)
        resources_dir = os.path.join(this_dir, 'resources')
        shutil.copy(os.path.join(resources_dir, 'scanview.css'), out_dir)
        shutil.copy(os.path.join(resources_dir, 'sorttable.js'), out_dir)
        shutil.copy(os.path.join(resources_dir, 'selectable.js'), out_dir)

    @trace
    def report(bugs, crashes):
        logging.debug('bugs: {0}, crashes: {1}'.format(bugs, crashes))
        result = (len(bugs) + len(crashes)) > 0
        if result:
            opts = filter_dict(args,
                               set(),
                               {'output': os.path.join(out_dir, 'index.html')})
            format_report(opts, bugs, crashes)
            copy_resource_files()
        return result

    bugs = dict()
    pool = multiprocessing.Pool(1 if args['sequential'] else None)
    for c in pool.imap_unordered(scan_file,
                                 glob.iglob(os.path.join(out_dir, '*.html'))):
        consume(bugs, c)
    pool.close()
    pool.join()

    return report(bugs, dict())  # TODO: collect crash reports


@trace
def scan_file(result):
    """ Parse out the bug information from HTML output. """
    patterns = frozenset(
        [re.compile('<!-- BUGTYPE (?P<bug_type>.*) -->$'),
         re.compile('<!-- BUGFILE (?P<bug_file>.*) -->$'),
         re.compile('<!-- BUGPATHLENGTH (?P<bug_path_length>.*) -->$'),
         re.compile('<!-- BUGLINE (?P<bug_line>.*) -->$'),
         re.compile('<!-- BUGCATEGORY (?P<bug_category>.*) -->$'),
         re.compile('<!-- BUGDESC (?P<bug_description>.*) -->$'),
         re.compile('<!-- FUNCTIONNAME (?P<bug_function>.*) -->$')])
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
def format_report(opts, bugs, crashes):
    import textwrap
    main = textwrap.dedent("""
        <!DOCTYPE html>
        <html>
          <head>
            <title>{html_title}</title>
            <link type="text/css" rel="stylesheet" href="scanview.css"/>
            <script type='text/javascript' src="sorttable.js"></script>
            <script type='text/javascript' src='selectable.js'></script>
          </head>
          <body>
            <h1>{html_title}</h1>
            <table>
              <tr><th>User:</th><td>{user_name}@{host_name}</td></tr>
              <tr><th>Working Directory:</th><td>{current_dir}</td></tr>
              <tr><th>Command Line:</th><td>{cmd_args}</td></tr>
              <tr><th>Clang Version:</th><td>{clang_version}</td></tr>
              <tr><th>Date:</th><td>{date}</td></tr>
        {version_section}
            </table>
        {bug_section}
        {crash_section}
          </body>
        </html>
        """).strip()

    bug_section = textwrap.dedent("""
        <h2>Bug Summary</h2>
        {bugs_summary}
        <h2>Reports</h2>
        <table class="sortable" style="table-layout:automatic">
          <thead>
            <tr>
              <td>Bug Group</td>
              <td class="sorttable_sorted">Bug Type
                <span id="sorttable_sortfwdind">&nbsp;&#x25BE;</span>
              </td>
              <td>File</td>
              <td class="Q">Line</td>
              <td class="Q">Path Length</td>
              <td class="sorttable_nosort"></td>
              <!-- REPORTBUGCOL -->
            </tr>
          </thead>
          <tbody>
        {bugs}
          </tbody>
        </table>
        """).strip()

    crash_section = textwrap.dedent("""
        <h2>Analyzer Failures</h2>
        {crashes}
        """).strip()

    with open(opts['output'], 'w') as handle:
        handle.write(
            main.format(
                html_title='{}',
                user_name='{}',
                host_name='{}',
                current_dir=os.getcwd(),
                cmd_args='{}',
                clang_version=get_clang_version(opts['clang']),
                date='{}',
                version_section='',
                bug_section='{}',
                crash_section='{}'))
