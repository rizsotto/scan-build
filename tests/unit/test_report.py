# SPDX-License-Identifier: MIT

import os
import os.path
import tempfile
import unittest

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
            crashes = list(sut.CrashReader.read(tmpdir))
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


class GetPrefixFromCompilationDatabaseTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(sut.commonprefix([]), "")

    @unittest.skipIf(IS_WINDOWS, "windows has different path patterns")
    def test_with_different_filenames(self):
        self.assertEqual(sut.commonprefix(["/tmp/a.c", "/tmp/b.c"]), "/tmp")

    @unittest.skipIf(IS_WINDOWS, "windows has different path patterns")
    def test_with_different_dirnames(self):
        self.assertEqual(sut.commonprefix(["/tmp/abs/a.c", "/tmp/ack/b.c"]), "/tmp")

    @unittest.skipIf(IS_WINDOWS, "windows has different path patterns")
    def test_no_common_prefix(self):
        self.assertEqual(sut.commonprefix(["/tmp/abs/a.c", "/usr/ack/b.c"]), "/")

    @unittest.skipIf(IS_WINDOWS, "windows has different path patterns")
    def test_with_single_file(self):
        self.assertEqual(sut.commonprefix(["/tmp/a.c"]), "/tmp")

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_with_different_filenames_on_windows(self):
        self.assertEqual(sut.commonprefix(["c:\\tmp\\a.c", "c:\\tmp\\b.c"]), "c:\\tmp")

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_with_different_dirnames_on_windows(self):
        self.assertEqual(sut.commonprefix(["c:\\tmp\\abs\\a.c", "c:\\tmp\\ack\\b.c"]), "c:\\tmp")

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_no_common_prefix_on_windows(self):
        self.assertEqual(sut.commonprefix(["z:\\tmp\\abs\\a.c", "z:\\usr\\ack\\b.c"]), "z:\\")

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_different_drive_on_windows(self):
        self.assertEqual(sut.commonprefix(["c:\\tmp\\abs\\a.c", "z:\\usr\\ack\\b.c"]), "")

    @unittest.skipIf(not IS_WINDOWS, "windows has different path patterns")
    def test_with_single_file_on_windows(self):
        self.assertEqual(sut.commonprefix(["z:\\tmp\\a.c"]), "z:\\tmp")


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
