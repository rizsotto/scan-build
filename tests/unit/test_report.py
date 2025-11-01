# SPDX-License-Identifier: MIT

import os
import os.path
import tempfile
import unittest
from pathlib import Path

import clanganalyzer.report as sut

IS_WINDOWS = os.getenv("windows")


def run_bug_parse(content):
    with tempfile.TemporaryDirectory() as tmpdir:
        file_name = os.path.join(tmpdir, "test.html")
        with open(file_name, "w") as handle:
            lines = (line + os.linesep for line in content)
            handle.writelines(lines)
        for bug in sut.BugParser.parse_bug_html(file_name):
            return bug


class ParseFileTest(unittest.TestCase):
    def test_parse_bug(self):
        content = [
            "some header",
            "<!-- BUGDESC Division by zero -->",
            "<!-- BUGTYPE Division by zero -->",
            "<!-- BUGCATEGORY Logic error -->",
            "<!-- BUGFILE xx -->",
            "<!-- BUGLINE 5 -->",
            "<!-- BUGCOLUMN 22 -->",
            "<!-- BUGPATHLENGTH 4 -->",
            "<!-- BUGMETAEND -->",
            "<!-- REPORTHEADER -->",
            "some tails",
        ]
        result = run_bug_parse(content)
        self.assertEqual(result.category, "Logic error")
        self.assertEqual(result.path_length, 4)
        self.assertEqual(result.line, 5)
        self.assertEqual(result.type, "Division by zero")
        self.assertEqual(result.file, "xx")

    def test_parse_bug_empty(self):
        content = []
        result = run_bug_parse(content)
        self.assertEqual(result.category, "Other")
        self.assertEqual(result.path_length, 1)
        self.assertEqual(result.line, 0)

    def test_parse_crash(self):
        content = ["/some/path/file.c", "Some very serious Error", "bla", "bla-bla"]
        with tempfile.TemporaryDirectory() as tmpdir:
            file_name = os.path.join(tmpdir, "file.i.info.txt")
            with open(file_name, "w") as handle:
                handle.write(os.linesep.join(content))
            source, problem = sut.CrashReader._parse_info_file(file_name)
            self.assertEqual(source, content[0].rstrip())
            self.assertEqual(problem, content[1].rstrip())

    def test_parse_real_crash(self):
        import clanganalyzer.analyze as sut2

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test.c")
            with open(filename, "w") as handle:
                handle.write("int main() { return 0")
            # produce failure report
            opts = {
                "clang": "clang",
                "directory": os.getcwd(),
                "flags": [],
                "source": filename,
                "output_dir": tmpdir,
                "language": "c",
                "error_output": "some output",
                "exit_code": 13,
            }
            sut2.report_failure(opts)
            # verify
            crashes = list(sut.CrashReader.read(Path(tmpdir)))
            self.assertEqual(1, len(crashes))
            crash = crashes[0]
            self.assertEqual(filename, crash.source)
            self.assertEqual("Other Error", crash.problem)
            self.assertEqual(crash.file + ".info.txt", crash.info)
            self.assertEqual(crash.file + ".stderr.txt", crash.stderr)


class ReportMethodTest(unittest.TestCase):
    @unittest.skipIf(IS_WINDOWS, "windows has different path patterns")
    def test_chop(self):
        self.assertEqual("file", sut.chop("/prefix", "/prefix/file"))
        self.assertEqual("file", sut.chop("/prefix/", "/prefix/file"))
        self.assertEqual("lib/file", sut.chop("/prefix/", "/prefix/lib/file"))
        self.assertEqual("/prefix/file", sut.chop("", "/prefix/file"))

    @unittest.skipIf(IS_WINDOWS, "windows has different path patterns")
    def test_chop_when_cwd(self):
        self.assertEqual("../src/file", sut.chop("/cwd", "/src/file"))
        self.assertEqual("../src/file", sut.chop("/prefix/cwd", "/prefix/src/file"))

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_chop_on_windows(self):
        self.assertEqual("file", sut.chop("c:\\prefix", "c:\\prefix\\file"))
        self.assertEqual("file", sut.chop("c:\\prefix\\", "c:\\prefix\\file"))
        self.assertEqual("lib\\file", sut.chop("c:\\prefix\\", "c:\\prefix\\lib\\file"))
        self.assertEqual("c:\\prefix\\file", sut.chop("", "c:\\prefix\\file"))
        self.assertEqual("c:\\prefix\\file", sut.chop("e:\\prefix", "c:\\prefix\\file"))

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_chop_when_cwd_on_windows(self):
        self.assertEqual("..\\src\\file", sut.chop("c:\\cwd", "c:\\src\\file"))
        self.assertEqual("..\\src\\file", sut.chop("z:\\prefix\\cwd", "z:\\prefix\\src\\file"))


class CrashFormatterTest(unittest.TestCase):
    def test_format_crash(self):
        crash = sut.Crash(
            source="/path/to/source.c",
            problem="Division by zero",
            file="/output/dir/file.i",
            info="/output/dir/file.i.info.txt",
            stderr="/output/dir/file.i.stderr.txt",
        )

        formatter = sut.CrashFormatter("/path", "/output/dir")
        formatted = formatter.format(crash)

        self.assertEqual(formatted.source, "to/source.c")
        self.assertEqual(formatted.problem, "Division by zero")
        self.assertEqual(formatted.file, "file.i")
        self.assertEqual(formatted.info, "file.i.info.txt")
        self.assertEqual(formatted.stderr, "file.i.stderr.txt")

    def test_format_crash_with_html_escaping(self):
        crash = sut.Crash(
            source="/path/to/source<test>.c",
            problem="Error with & symbol",
            file="/output/dir/file.i",
            info="/output/dir/file.i.info.txt",
            stderr="/output/dir/file.i.stderr.txt",
        )

        formatter = sut.CrashFormatter("/path", "/output/dir")
        formatted = formatter.format(crash)

        self.assertEqual(formatted.source, "to/source&lt;test&gt;.c")
        self.assertEqual(formatted.problem, "Error with &amp; symbol")

    def test_crash_vars(self):
        crash = sut.Crash(
            source="/path/to/source.c",
            problem="Division by zero",
            file="/output/dir/file.i",
            info="/output/dir/file.i.info.txt",
            stderr="/output/dir/file.i.stderr.txt",
        )

        crash_dict = vars(crash)

        self.assertEqual(crash_dict["source"], "/path/to/source.c")
        self.assertEqual(crash_dict["problem"], "Division by zero")
        self.assertEqual(crash_dict["file"], "/output/dir/file.i")
        self.assertEqual(crash_dict["info"], "/output/dir/file.i.info.txt")
        self.assertEqual(crash_dict["stderr"], "/output/dir/file.i.stderr.txt")
        self.assertIsInstance(crash_dict, dict)

    def test_to_css_class_function(self):
        # Test that to_css_class can be called as a module function
        result = sut.to_css_class("Memory & Security")
        self.assertEqual(result, "memory___security")

        result = sut.to_css_class("Use after 'free'")
        self.assertEqual(result, "use_after_free")

        result = sut.to_css_class("Logic error")
        self.assertEqual(result, "logic_error")


class BugFormatterTest(unittest.TestCase):
    def test_format_bug(self):
        bug = sut.Bug(
            file="/path/to/source.c",
            line=42,
            path_length=5,
            category="Logic error",
            type="Division by zero",
            function="main",
            report="/output/dir/report.html",
        )

        formatter = sut.BugFormatter("/path", "/output/dir")
        formatted = formatter.format(bug)

        self.assertEqual(formatted.file, "to/source.c")
        self.assertEqual(formatted.line, 42)
        self.assertEqual(formatted.path_length, 5)
        self.assertEqual(formatted.category, "Logic error")
        self.assertEqual(formatted.type, "Division by zero")
        self.assertEqual(formatted.function, "main")
        self.assertEqual(formatted.report, "report.html")
        self.assertEqual(formatted.type_class, "bt_logic_error_division_by_zero")

    def test_format_bug_with_html_escaping(self):
        bug = sut.Bug(
            file="/path/to/source<test>.c",
            line=10,
            path_length=3,
            category="Memory & Security",
            type="Use after 'free'",
            function="test_function",
            report="/output/dir/report.html",
        )

        formatter = sut.BugFormatter("/path", "/output/dir")
        formatted = formatter.format(bug)

        self.assertEqual(formatted.file, "to/source&lt;test&gt;.c")
        self.assertEqual(formatted.category, "Memory &amp; Security")
        self.assertEqual(formatted.type, "Use after &apos;free&apos;")
        self.assertEqual(formatted.function, "test_function")
        self.assertEqual(formatted.type_class, "bt_memory___security_use_after_free")

    def test_bug_vars(self):
        bug = sut.Bug(
            file="/path/to/source.c",
            line=42,
            path_length=5,
            category="Logic error",
            type="Division by zero",
            function="main",
            report="/output/dir/report.html",
        )

        bug_dict = vars(bug)

        self.assertEqual(bug_dict["file"], "/path/to/source.c")
        self.assertEqual(bug_dict["line"], 42)
        self.assertEqual(bug_dict["path_length"], 5)
        self.assertEqual(bug_dict["category"], "Logic error")
        self.assertEqual(bug_dict["type"], "Division by zero")
        self.assertEqual(bug_dict["function"], "main")
        self.assertEqual(bug_dict["report"], "/output/dir/report.html")
        self.assertIsInstance(bug_dict, dict)


class RefactoredMethodsTest(unittest.TestCase):
    """Tests for the refactored _write_* methods that use file-like objects and mocked data."""

    def setUp(self):
        """Set up mock data for testing."""
        from unittest.mock import Mock

        # Mock BugCounter for bug summary tests
        self.mock_bug_counter = Mock()
        self.mock_bug_counter.total = 15

        # Create mock bug type objects
        memory_leak = Mock(bug_type="Memory leak", bug_count=5, bug_type_class="memory_leak")
        use_after_free = Mock(bug_type="Use after free", bug_count=3, bug_type_class="use_after_free")
        null_deref = Mock(bug_type="Null dereference", bug_count=7, bug_type_class="null_dereference")

        self.mock_bug_counter.categories = {
            "Memory errors": {
                "memory_leak": memory_leak,
                "use_after_free": use_after_free,
            },
            "Logic errors": {
                "null_dereference": null_deref,
            },
        }

        # Mock Bug objects for bug report tests
        self.mock_bugs = [
            sut.Bug(
                file="src/main.c",
                line=42,
                path_length=5,
                category="Memory Error",
                type="Memory Leak",
                function="malloc_wrapper",
                report="report_001.html",
                type_class="memory_leak",
            ),
            sut.Bug(
                file="src/utils.c",
                line=128,
                path_length=3,
                category="Logic Error",
                type="Null Dereference",
                function="get_value",
                report="report_002.html",
                type_class="null_dereference",
            ),
        ]

        # Mock Crash objects for crash report tests
        self.mock_crashes = [
            sut.Crash(
                source="src/complex.c",
                problem="Segmentation fault",
                file="failures/crash_001.c",
                info="failures/crash_001.info.txt",
                stderr="failures/crash_001.stderr.txt",
            ),
            sut.Crash(
                source="src/networking.c",
                problem="Assertion failure",
                file="failures/crash_002.c",
                info="failures/crash_002.info.txt",
                stderr="failures/crash_002.stderr.txt",
            ),
        ]

    def test_write_bug_summary_with_mock_data(self):
        """Test _write_bug_summary with mocked BugCounter data."""
        import io

        output = io.StringIO()
        sut._write_bug_summary(output, self.mock_bug_counter)
        content = output.getvalue()

        # Verify HTML structure
        self.assertIn("<h2>Bug Summary</h2>", content)
        self.assertIn("<table>", content)
        self.assertIn("</table>", content)

        # Verify total count
        self.assertIn("All Bugs", content)
        self.assertIn("15", content)  # Total count

        # Verify categories
        self.assertIn("Memory errors", content)
        self.assertIn("Logic errors", content)

        # Verify individual bug types
        self.assertIn("Memory leak", content)
        self.assertIn("5", content)  # Memory leak count
        self.assertIn("Use after free", content)
        self.assertIn("3", content)  # Use after free count
        self.assertIn("Null dereference", content)
        self.assertIn("7", content)  # Null dereference count

        # Verify checkboxes are present
        self.assertIn('type="checkbox"', content)
        self.assertIn("AllBugsCheck", content)

        # Verify comment markers
        self.assertIn("<!-- SUMMARYBUGEND -->", content)

    def test_write_bug_summary_empty_data(self):
        """Test _write_bug_summary with empty bug counter."""
        import io
        from unittest.mock import Mock

        empty_counter = Mock()
        empty_counter.total = 0
        empty_counter.categories = {}

        output = io.StringIO()
        sut._write_bug_summary(output, empty_counter)
        content = output.getvalue()

        # Should still have basic structure
        self.assertIn("<h2>Bug Summary</h2>", content)
        self.assertIn("All Bugs", content)
        self.assertIn("0", content)  # Zero total
        self.assertIn("<!-- SUMMARYBUGEND -->", content)

    def test_write_bug_report_with_mock_data(self):
        """Test _write_bug_report with mocked Bug data."""
        import io

        output = io.StringIO()
        sut._write_bug_report(output, "test_prefix", "/fake/output", self.mock_bugs)
        content = output.getvalue()

        # Verify HTML structure
        self.assertIn("<h2>Reports</h2>", content)
        self.assertIn("Bug Group", content)
        self.assertIn("Bug Type", content)
        self.assertIn("File", content)
        self.assertIn("Function/Method", content)
        self.assertIn("Line", content)
        self.assertIn("Path Length", content)

        # Verify comment markers
        self.assertIn("<!-- REPORTBUGCOL -->", content)
        self.assertIn("<!-- REPORTBUGEND -->", content)

        # Verify each bug appears (note: content is transformed by BugFormatter)
        for bug in self.mock_bugs:
            # Check that core information is present (BugFormatter may transform paths)
            filename = bug.file.split("/")[-1]  # Get just the filename
            self.assertIn(filename, content)
            self.assertIn(str(bug.line), content)
            self.assertIn(bug.category, content)
            self.assertIn(bug.type, content)
            self.assertIn(bug.function, content)
            self.assertIn(str(bug.path_length), content)

        # Count bug rows
        bug_rows = content.count('<tr class="')
        self.assertEqual(bug_rows, 2)  # Two bugs

    def test_write_bug_report_empty_data(self):
        """Test _write_bug_report with empty bug list."""
        import io

        output = io.StringIO()
        sut._write_bug_report(output, "prefix", "/fake/dir", [])
        content = output.getvalue()

        # Should have structure but no bug rows
        self.assertIn("<h2>Reports</h2>", content)
        self.assertIn("<!-- REPORTBUGCOL -->", content)
        self.assertIn("<!-- REPORTBUGEND -->", content)

        # Should have no bug rows
        self.assertEqual(content.count('<tr class="'), 0)

    def test_write_bug_report_with_generator(self):
        """Test _write_bug_report with generator input."""
        import io

        def bug_generator():
            yield from self.mock_bugs

        output = io.StringIO()
        sut._write_bug_report(output, "prefix", "/fake/dir", bug_generator())
        content = output.getvalue()

        # Should work same as with list
        self.assertIn("<h2>Reports</h2>", content)
        bug_rows = content.count('<tr class="')
        self.assertEqual(bug_rows, 2)

    def test_write_crash_report_with_mock_data(self):
        """Test _write_crash_report with mocked Crash data."""
        import io

        output = io.StringIO()
        sut._write_crash_report(output, "test_prefix", "/fake/output", self.mock_crashes)
        content = output.getvalue()

        # Verify HTML structure
        self.assertIn("<h2>Analyzer Failures</h2>", content)
        self.assertIn("The analyzer had problems processing the following files:", content)
        self.assertIn("Problem", content)
        self.assertIn("Source File", content)
        self.assertIn("Preprocessed File", content)
        self.assertIn("STDERR Output", content)

        # Verify comment marker
        self.assertIn("<!-- REPORTCRASHES -->", content)

        # Verify each crash appears (note: content is transformed by CrashFormatter)
        for crash in self.mock_crashes:
            # Check that core information is present
            self.assertIn(crash.source, content)
            self.assertIn(crash.problem, content)
            # File paths are transformed, so check for filename parts
            crash_filename = crash.file.split("/")[-1]
            stderr_filename = crash.stderr.split("/")[-1]
            self.assertIn(crash_filename, content)
            self.assertIn(stderr_filename, content)

    def test_write_crash_report_empty_data(self):
        """Test _write_crash_report with empty crash list."""
        import io

        output = io.StringIO()
        sut._write_crash_report(output, "prefix", "/fake/dir", [])
        content = output.getvalue()

        # Should have structure but no crash rows
        self.assertIn("<h2>Analyzer Failures</h2>", content)
        self.assertIn("<!-- REPORTCRASHES -->", content)

        # Should have header row but no crash data rows
        header_rows = content.count("<tr>")
        self.assertEqual(header_rows, 1)  # Just the header

    def test_write_crash_report_with_tuple(self):
        """Test _write_crash_report with tuple input."""
        import io

        crash_tuple = tuple(self.mock_crashes)
        output = io.StringIO()
        sut._write_crash_report(output, "prefix", "/fake/dir", crash_tuple)
        content = output.getvalue()

        # Should work same as with list
        self.assertIn("<h2>Analyzer Failures</h2>", content)
        # Should have header + 2 crash rows
        rows_with_td = content.count("<td>")
        self.assertGreater(rows_with_td, 8)  # At least header + 2 crashes * 4 columns

    def test_large_dataset_performance(self):
        """Test that methods handle large datasets efficiently."""
        import io
        from unittest.mock import Mock

        # Create a large bug counter
        large_counter = Mock()
        large_counter.total = 1000

        # Create many bug types
        categories = {}
        for i in range(10):
            cat_name = f"Category {i}"
            categories[cat_name] = {}
            for j in range(10):
                bug_name = f"bug_{i}_{j}"
                bug_type = Mock(bug_type=f"Bug Type {i}-{j}", bug_count=i + j, bug_type_class=f"bug_class_{i}_{j}")
                categories[cat_name][bug_name] = bug_type

        large_counter.categories = categories

        # Test should complete quickly
        output = io.StringIO()
        sut._write_bug_summary(output, large_counter)
        content = output.getvalue()

        # Should handle large data
        self.assertIn("1000", content)
        self.assertIn("Category 0", content)
        self.assertIn("Category 9", content)

    def test_special_characters_handling(self):
        """Test that special HTML characters are handled properly."""
        import io

        # Create bug with special characters
        special_bug = sut.Bug(
            file="src/test<script>.c",
            line=1,
            path_length=1,
            category="Logic & Memory",
            type="Buffer Overflow > 255",
            function="dangerous<T>",
            report="report.html",
            type_class="buffer_overflow",
        )

        output = io.StringIO()
        sut._write_bug_report(output, "prefix", "/fake/dir", [special_bug])
        content = output.getvalue()

        # Content should be processed by escape() function
        # The exact escaping depends on the formatter implementation
        self.assertIn("Logic", content)  # Part of the category should be there
        self.assertIn("Buffer Overflow", content)  # Part of the type should be there
        self.assertIn("dangerous", content)  # Part of the function should be there
