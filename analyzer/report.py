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
import textwrap
from analyzer.decorators import trace
from analyzer.driver import filter_dict, get_clang_version


class Crashes(object):

    @trace
    def __init__(self, out_dir):
        self.count = 0
        self.line_template = textwrap.dedent(
            """
            <tr>
              <td>{problem}</td>
              <td>{source}</td>
              <td><a href="{preproc}">preprocessor output</a></td>
              <td><a href="{stderr}">analyzer std err</a></td>
            </tr>""").lstrip()
        self.name = os.path.join(out_dir, 'crashes.html.fragment')
        self.handle = open(self.name, 'w')

    @trace
    def add(self, report):
        self.count += 1
        self.handle.write(self.line_template.format(**report))

    @trace
    def close(self):
        self.handle.close()
        os.remove(self.name)

    @trace
    def concat_to_report(self, report):
        self.handle.close()
        if self.count:
            with open(self.name, 'r') as handle:
                report.write(
                    textwrap.dedent(
                        """
                        <table>
                          <thead>
                            <tr>
                              <td>Problem</td>
                              <td>Source File</td>
                              <td>Preprocessed File</td>
                              <td>STDERR Output</td>
                            </tr>
                          </thead>
                          <tbody>
                        """).lstrip())
                # copy line by line
                for line in handle:
                    report.write(line)
                report.write("\n  </tbody>\n</table>")


class Bugs(object):

    @trace
    def __init__(self, out_dir):
        self.count = 0
        self.line_template = textwrap.dedent(
            """
            <tr>
              <td class="DESC">{bug_category}</td>
              <td class="DESC">{bug_type}</td>
              <td>{bug_file}</td>
              <td class="Q">{bug_line}</td>
              <td class="Q">{bug_path_length}</td>
              <td><a href="{report_file}#EndPath">View Report</a></td>
            </tr>""").lstrip()
        self.name = os.path.join(out_dir, 'bugs.html.fragment')
        self.handle = open(self.name, 'w')

    @trace
    def add(self, report):
        self.count += 1
        self.handle.write(self.line_template.format(**report))

    @trace
    def close(self):
        self.handle.close()
        os.remove(self.name)

    def etwas():
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
            """).lstrip()

    @trace
    def concat_to_report(self, report):
        self.handle.close()
        if self.count:
            with open(self.name, 'r') as handle:
                report.write(
                    textwrap.dedent(
                        """
                        <table class="sortable" style="table-layout:automatic">
                          <thead>
                            <tr>
                              <td>Bug Group</td>
                              <td class="sorttable_sorted">
                                Bug Type
                                <span id="sorttable_sortfwdind">&nbsp;&#x25BE;
                                </span>
                              </td>
                              <td>File</td>
                              <td class="Q">Line</td>
                              <td class="Q">Path Length</td>
                              <td class="sorttable_nosort"></td>
                            </tr>
                          </thead>
                          <tbody>
                        """).lstrip())
                # copy line by line
                for line in handle:
                    report.write(line)
                report.write("\n  </tbody>\n</table>")


class ReportGenerator(object):

    def __init__(self, args, out_dir):
        self.args = args
        self.out_dir = out_dir
        self.crashes = Crashes(out_dir)
        self.bugs = Bugs(out_dir)

    # PEP 0343 requuires this
    def __enter__(self):
        return self

    # PEP 0343 requuires this
    def __exit__(self, type, value, traceback):
        self.crashes.close()
        self.bugs.close()

    # public interface for beye
    @trace
    def crash(self, report):
        self.crashes.add(report)

    # public interface for beye
    @trace
    def create_report(self):
        pattern = os.path.join(self.out_dir, '*.html')
        pool = multiprocessing.Pool(1 if 'sequential' in self.args else None)
        count = 0
        for c in pool.imap_unordered(scan_file, glob.iglob(pattern)):
            self.bugs.add(c)
            count += 1
        pool.close()
        pool.join()

        if count:
            format_report(self.args, self.out_dir, self.bugs, self.crashes)
            copy_resource_files(self.out_dir)
        return count


@trace
def create_report_generator(opts, out_dir):
    def report_requested():
        output_format = opts.get('output_format')
        return 'html' == output_format or 'plist-html' == output_format

    class Fake(object):

        def __init__(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            pass

        def crash(self, report):
            pass

        def create_report(self):
            return 0

    return ReportGenerator(opts, out_dir) if report_requested() else Fake()


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
def format_report(opts, out_dir, bugs, crashes):
    import getpass
    import socket
    import sys
    import datetime

    def default_title():
        return os.getcwd() + ' - analyzer results'

    output = os.path.join(out_dir, 'index.html')
    with open(output, 'w') as handle:
        handle.write(
            textwrap.dedent("""
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
            """).lstrip()
                .format(
                    html_title=opts.get('html_title', default_title()),
                    user_name=getpass.getuser(),
                    host_name=socket.getfqdn(),
                    current_dir=os.getcwd(),
                    cmd_args=' '.join(sys.argv),
                    clang_version=get_clang_version(opts['clang']),
                    date=datetime.datetime.today().strftime('%c'),
                    version_section=''))
        bugs.concat_to_report(handle)
        crashes.concat_to_report(handle)
        handle.write("\n  </body>\n</html>")


@trace
def copy_resource_files(out_dir):
    this_dir, _ = os.path.split(__file__)
    resources_dir = os.path.join(this_dir, 'resources')
    shutil.copy(os.path.join(resources_dir, 'scanview.css'), out_dir)
    shutil.copy(os.path.join(resources_dir, 'sorttable.js'), out_dir)
    shutil.copy(os.path.join(resources_dir, 'selectable.js'), out_dir)
