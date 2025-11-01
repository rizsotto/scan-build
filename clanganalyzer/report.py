# SPDX-License-Identifier: MIT
"""This module is responsible to generate 'index.html' for the report.

The input for this step is the output directory, where individual reports
could be found. It parses those reports and generates 'index.html'."""

import argparse
import datetime
import getpass
import glob
import itertools
import json
import logging
import os
import os.path
import plistlib
import re
import shutil
import socket
import sys
from collections.abc import Generator, Iterator
from dataclasses import dataclass, field

from clanganalyzer.clang import get_version

__all__ = ["document"]


def document(args: argparse.Namespace) -> int:
    """Generates cover report and returns the number of bugs/crashes."""

    html_reports_available = args.output_format in {"html", "plist-html"}

    logging.debug("count crashes and bugs")
    crash_count = sum(1 for _ in CrashReader.read(args.output))
    bug_counter = BugCounter()
    for bug in BugParser.read_bugs(args.output, html_reports_available):
        bug_counter(bug)
    result = crash_count + bug_counter.total

    if html_reports_available and result:
        use_cdb = os.path.exists(args.cdb)

        logging.debug("generate index.html file")
        # common prefix for source files to have sorter path
        prefix = commonprefix_from(args.cdb) if use_cdb else os.getcwd()
        # assemble the cover from multiple fragments
        fragments: list[str] = []
        try:
            if bug_counter.total:
                fragments.append(bug_summary(args.output, bug_counter))
                fragments.append(bug_report(args.output, prefix))
            if crash_count:
                fragments.append(crash_report(args.output, prefix))
            assemble_cover(args, prefix, fragments)
            # copy additional files to the report
            copy_resource_files(args.output)
            if use_cdb:
                shutil.copy(args.cdb, args.output)
        finally:
            for fragment in fragments:
                os.remove(fragment)
    return result


def assemble_cover(args: argparse.Namespace, prefix: str, fragments: list[str]) -> None:
    """Put together the fragments into a final report."""

    html_title = args.html_title if args.html_title else os.path.basename(prefix) + " - analyzer results"
    user_name = getpass.getuser()
    host_name = socket.gethostname()
    cmd_args = " ".join(sys.argv)
    clang_version = get_version(args.clang)
    date = datetime.datetime.today().strftime("%c")

    with open(os.path.join(args.output, "index.html"), "w") as handle:
        indent = 0
        _ = handle.write(
            reindent(
                f"""
        |<!DOCTYPE html>
        |<html>
        |  <head>
        |    <title>{args.html_title}</title>
        |    <link type="text/css" rel="stylesheet" href="scanview.css"/>
        |    <script type='text/javascript' src="sorttable.js"></script>
        |    <script type='text/javascript' src='selectable.js'></script>
        |  </head>
        |<!-- SUMMARYENDHEAD -->
        |  <body>
        |    <h1>{html_title}</h1>
        |    <table>
        |      <tr><th>User:</th><td>{user_name}@{host_name}</td></tr>
        |      <tr><th>Working Directory:</th><td>{prefix}</td></tr>
        |      <tr><th>Command Line:</th><td>{cmd_args}</td></tr>
        |      <tr><th>Clang Version:</th><td>{clang_version}</td></tr>
        |      <tr><th>Date:</th><td>{date}</td></tr>
        |    </table>""",
                indent,
            )
        )
        for fragment in fragments:
            # copy the content of fragments
            with open(fragment) as input_handle:
                shutil.copyfileobj(input_handle, handle)
        _ = handle.write(
            reindent(
                """
        |  </body>
        |</html>""",
                indent,
            )
        )


def bug_summary(output_dir: str, bug_counter: "BugCounter") -> str:
    """Bug summary is a HTML table to give a better overview of the bugs."""

    name = os.path.join(output_dir, "summary.html.fragment")
    with open(name, "w") as handle:
        indent = 4
        _ = handle.write(
            reindent(
                f"""
        |<h2>Bug Summary</h2>
        |<table>
        |  <thead>
        |    <tr>
        |      <td>Bug Type</td>
        |      <td>Quantity</td>
        |      <td class="sorttable_nosort">Display?</td>
        |    </tr>
        |  </thead>
        |  <tbody>
        |    <tr style="font-weight:bold">
        |      <td class="SUMM_DESC">All Bugs</td>
        |      <td class="Q">{bug_counter.total}</td>
        |      <td>
        |        <center>
        |          <input checked type="checkbox" id="AllBugsCheck"
        |                 onClick="CopyCheckedStateToCheckButtons(this);"/>
        |        </center>
        |      </td>
        |    </tr>""",
                indent,
            )
        )
        for category, types in bug_counter.categories.items():
            _ = handle.write(
                reindent(
                    f"""
        |    <tr>
        |      <th>{category}</th><th colspan=2></th>
        |    </tr>""",
                    indent,
                )
            )
            for bug_type in types.values():
                _ = handle.write(
                    reindent(
                        f"""
        |    <tr>
        |      <td class="SUMM_DESC">{bug_type.bug_type}</td>
        |      <td class="Q">{bug_type.bug_count}</td>
        |      <td>
        |        <center>
        |          <input checked type="checkbox"
        |                 onClick="ToggleDisplay(this,'{bug_type.bug_type_class}');"/>
        |        </center>
        |      </td>
        |    </tr>""",
                        indent,
                    )
                )
        _ = handle.write(
            reindent(
                """
        |  </tbody>
        |</table>""",
                indent,
            )
        )
        _ = handle.write(comment("SUMMARYBUGEND"))
    return name


def bug_report(output_dir: str, prefix: str) -> str:
    """Creates a fragment from the analyzer reports."""

    name = os.path.join(output_dir, "bugs.html.fragment")
    with open(name, "w") as handle:
        indent = 4
        _ = handle.write(
            reindent(
                """
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
        |      <td>Function/Method</td>
        |      <td class="Q">Line</td>
        |      <td class="Q">Path Length</td>
        |      <td class="sorttable_nosort"></td>
        |    </tr>
        |  </thead>
        |  <tbody>""",
                indent,
            )
        )
        _ = handle.write(comment("REPORTBUGCOL"))
        formatter = BugFormatter(prefix, output_dir)
        for bug in BugParser.read_bugs(output_dir, True):
            current = formatter.format(bug)
            _ = handle.write(
                reindent(
                    f"""
        |    <tr class="{current.type_class}">
        |      <td class="DESC">{current.category}</td>
        |      <td class="DESC">{current.type}</td>
        |      <td>{current.file}</td>
        |      <td class="DESC">{current.function}</td>
        |      <td class="Q">{current.line}</td>
        |      <td class="Q">{current.path_length}</td>
        |      <td><a href="{current.report}#EndPath">View Report</a></td>
        |    </tr>""",
                    indent,
                )
            )
            _ = handle.write(comment("REPORTBUG", vars(current)))
        _ = handle.write(
            reindent(
                """
        |  </tbody>
        |</table>""",
                indent,
            )
        )
        _ = handle.write(comment("REPORTBUGEND"))
    return name


def crash_report(output_dir: str, prefix: str) -> str:
    """Creates a fragment from the compiler crashes."""

    name = os.path.join(output_dir, "crashes.html.fragment")
    with open(name, "w") as handle:
        indent = 4
        _ = handle.write(
            reindent(
                """
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
        |  <tbody>""",
                indent,
            )
        )
        formatter = CrashFormatter(prefix, output_dir)
        for crash in CrashReader.read(output_dir):
            current = formatter.format(crash)
            _ = handle.write(
                reindent(
                    f"""
        |    <tr>
        |      <td>{current.problem}</td>
        |      <td>{current.source}</td>
        |      <td><a href="{current.file}">preprocessor output</a></td>
        |      <td><a href="{current.stderr}">analyzer std err</a></td>
        |    </tr>""",
                    indent,
                )
            )
            _ = handle.write(comment("REPORTPROBLEM", vars(current)))
        _ = handle.write(
            reindent(
                """
        |  </tbody>
        |</table>""",
                indent,
            )
        )
        _ = handle.write(comment("REPORTCRASHES"))
    return name


@dataclass
class Crash:
    source: str
    problem: str
    file: str
    info: str
    stderr: str


class CrashReader:
    """Reads crash information from files and creates Crash instances."""

    @classmethod
    def _parse_info_file(cls, filename: str) -> tuple[str, str] | None:
        """Parse out the crash information from the report file."""

        lines = list(safe_readlines(filename))
        return None if len(lines) < 2 else (lines[0], lines[1])

    @classmethod
    def read(cls, output_dir: str) -> Iterator[Crash]:
        """Generate a unique sequence of crashes from given directory."""

        pattern = os.path.join(output_dir, "failures", "*.info.txt")
        for info_filename in glob.iglob(pattern):
            base_filename = info_filename[0 : -len(".info.txt")]
            stderr_filename = f"{base_filename}.stderr.txt"

            source_and_problem = cls._parse_info_file(info_filename)
            if source_and_problem is not None:
                yield Crash(
                    source=source_and_problem[0],
                    problem=source_and_problem[1],
                    file=base_filename,
                    info=info_filename,
                    stderr=stderr_filename,
                )


class CrashFormatter:
    """Formats Crash instances for safe HTML rendering."""

    def __init__(self, prefix: str, output_dir: str):
        """Initialize formatter with prefix and output directory."""
        self.prefix: str = prefix
        self.output_dir: str = output_dir

    def format(self, crash: Crash) -> Crash:
        """Create a new Crash instance with escaped and chopped attributes."""
        return Crash(
            source=escape(chop(self.prefix, crash.source)),
            problem=escape(crash.problem),
            file=escape(chop(self.output_dir, crash.file)),
            info=escape(chop(self.output_dir, crash.info)),
            stderr=escape(chop(self.output_dir, crash.stderr)),
        )


@dataclass(eq=False)
class Bug:
    file: str
    line: int
    path_length: int
    category: str
    type: str
    function: str
    report: str
    type_class: str = ""

    def __eq__(self, o: object) -> bool:
        return (
            isinstance(o, Bug)
            and o.line == self.line
            and o.path_length == self.path_length
            and o.type == self.type
            and o.file == self.file
        )

    def __hash__(self) -> int:
        return hash((self.line, self.path_length, self.type, self.file))


class BugParser:
    """Parses bug information from files and creates Bug instances."""

    @staticmethod
    def from_attributes(report: str, attributes: dict[str, str]) -> Bug:
        """Create a Bug instance from a report path and attributes dictionary."""
        return Bug(
            file=attributes.get("bug_file", ""),
            line=int(attributes.get("bug_line", "0")),
            path_length=int(attributes.get("bug_path_length", "1")),
            category=attributes.get("bug_category", "Other"),
            type=attributes.get("bug_type", ""),
            function=attributes.get("bug_function", "n/a"),
            report=report,
        )

    @staticmethod
    def parse_bug_plist(filename: str) -> Generator[Bug, None, None]:
        """Returns the generator of bugs from a single .plist file."""

        with open(filename, "rb") as handle:
            content = plistlib.load(handle)
            files = content.get("files", [])
            for bug in content.get("diagnostics", []):
                if len(files) <= int(bug["location"]["file"]):
                    logging.warning('Parsing bug from "%s" failed', filename)
                    continue

                yield BugParser.from_attributes(
                    filename,
                    {
                        "bug_type": bug["type"],
                        "bug_category": bug["category"],
                        "bug_line": bug["location"]["line"],
                        "bug_path_length": bug["location"]["col"],
                        "bug_file": files[int(bug["location"]["file"])],
                    },
                )

    @staticmethod
    def parse_bug_html(filename: str) -> Generator[Bug, None, None]:
        """Parse out the bug information from HTML output."""

        patterns = [
            re.compile(r"<!-- BUGTYPE (?P<bug_type>.*) -->$"),
            re.compile(r"<!-- BUGFILE (?P<bug_file>.*) -->$"),
            re.compile(r"<!-- BUGPATHLENGTH (?P<bug_path_length>.*) -->$"),
            re.compile(r"<!-- BUGLINE (?P<bug_line>.*) -->$"),
            re.compile(r"<!-- BUGCATEGORY (?P<bug_category>.*) -->$"),
            re.compile(r"<!-- FUNCTIONNAME (?P<bug_function>.*) -->$"),
        ]
        endsign = re.compile(r"<!-- BUGMETAEND -->")

        bug = {}
        for line in safe_readlines(filename):
            # do not read the file further
            if endsign.match(line):
                break
            # search for the right lines
            for regex in patterns:
                match = regex.match(line.strip())
                if match:
                    bug.update(match.groupdict())
                    break

        yield BugParser.from_attributes(filename, bug)

    @staticmethod
    def read_bugs(output_dir: str, html: bool) -> Generator[Bug, None, None]:
        """Generate a unique sequence of bugs from given output directory.

        Duplicates can be in a project if the same module was compiled multiple
        times with different compiler options. These would be better to show in
        the final report (cover) only once."""

        def empty(file_name: str):
            return os.stat(file_name).st_size == 0

        # get the right parser for the job.
        parser = BugParser.parse_bug_html if html else BugParser.parse_bug_plist
        # get the input files, which are not empty.
        pattern = os.path.join(output_dir, "*.html" if html else "*.plist")
        files = (file for file in glob.iglob(pattern) if not empty(file))
        # do the parsing job.
        return BugParser.unique_bugs(itertools.chain.from_iterable(parser(filename) for filename in files))

    @staticmethod
    def unique_bugs(generator: Iterator[Bug]) -> Generator[Bug, None, None]:
        """Make unique generator from a given input generator."""

        state: set[Bug] = set()
        for item in generator:
            if item not in state:
                state.add(item)
                yield item


class BugFormatter:
    """Formats Bug instances for safe HTML rendering."""

    def __init__(self, prefix: str, output_dir: str):
        """Initialize formatter with prefix and output directory."""
        self.prefix: str = prefix
        self.output_dir: str = output_dir

    def format(self, bug: Bug) -> Bug:
        """Create a new Bug instance with escaped and chopped attributes."""

        type_class = "_".join(["bt", to_css_class(bug.category), to_css_class(bug.type)])

        return Bug(
            file=escape(chop(self.prefix, bug.file)),
            line=bug.line,
            path_length=bug.path_length,
            category=escape(bug.category),
            type=escape(bug.type),
            function=escape(bug.function),
            report=escape(chop(self.output_dir, bug.report)),
            type_class=type_class,
        )


@dataclass
class BugCounter:
    """Counters for bug statistics.

    Two entries are maintained: 'total' is an integer, represents the
    number of bugs. The 'categories' is a two level categorisation of bug
    counters. The first level is 'bug category' the second is 'bug type'.
    Each entry in this classification contains type and count information."""

    @dataclass
    class CountPerType:
        """Counter for a specific bug type."""

        bug_type: str
        bug_type_class: str
        bug_count: int = 0

    total: int = 0
    categories: dict[str, dict[str, "BugCounter.CountPerType"]] = field(default_factory=dict)

    def __call__(self, bug: Bug) -> None:
        if bug.category not in self.categories:
            self.categories[bug.category] = {}

        current_category = self.categories[bug.category]

        if bug.type not in current_category:
            type_class = "_".join(["bt", to_css_class(bug.category), to_css_class(bug.type)])
            current_category[bug.type] = BugCounter.CountPerType(bug_type=bug.type, bug_type_class=type_class)

        current_category[bug.type].bug_count += 1
        self.total += 1


def copy_resource_files(output_dir: str) -> None:
    """Copy the javascript and css files to the report directory."""

    this_dir = os.path.dirname(os.path.realpath(__file__))
    for resource in os.listdir(os.path.join(this_dir, "resources")):
        shutil.copy(os.path.join(this_dir, "resources", resource), output_dir)


def safe_readlines(filename: str) -> Iterator[str]:
    """Read and return an iterator of lines from file."""

    with open(filename, mode="rb") as handler:
        for line in handler.readlines():
            # this is a workaround to fix windows read '\r\n' as new lines.
            yield line.decode(errors="ignore").rstrip()


def chop(prefix: str, filename: str) -> str:
    """Create 'filename' from '/prefix/filename'"""
    result: str = filename
    if prefix:
        try:
            result = str(os.path.relpath(filename, prefix))
        except ValueError:
            pass
    return result


def to_css_class(text: str) -> str:
    """Convert text to a valid CSS class name."""
    return text.lower().replace(" ", "_").replace("'", "").replace("&", "_")


def escape(text: str) -> str:
    """Paranoid HTML escape method."""

    escape_table = {"&": "&amp;", '"': "&quot;", "'": "&apos;", ">": "&gt;", "<": "&lt;"}
    return "".join(escape_table.get(c, c) for c in text)


def reindent(text: str, indent: int) -> str:
    """Utility function to format html output and keep indentation."""

    result: str = ""
    for line in text.splitlines():
        if line.strip():
            result += (" " * indent) + line.split("|")[1] + os.linesep
    return result


def comment(name: str, opts: dict[str, str] | None = None) -> str:
    """Utility function to format meta information as comment."""

    if opts:
        attributes = "".join(f' {key}="{value}"' for key, value in opts.items())
    else:
        attributes = ""

    return f"<!-- {name}{attributes} -->{os.linesep}"


def commonprefix_from(filename: str) -> str:
    """Create file prefix from a compilation database entries."""

    with open(filename) as handle:
        return commonprefix(item["file"] for item in json.load(handle))


def commonprefix(files: Iterator[str]) -> str:
    """Fixed version of os.path.commonprefix.

    :param files: list of file names.
    :return: the longest path prefix that is a prefix of all files."""
    result = None
    for current in files:
        if result is not None:
            result = os.path.commonprefix([result, current])
        else:
            result = current

    if result is None:
        return ""
    elif not os.path.isdir(result):
        return os.path.dirname(result)
    return os.path.abspath(result)
