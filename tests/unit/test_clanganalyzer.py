# SPDX-License-Identifier: MIT

import subprocess
import sys
import unittest

import clanganalyzer as sut


class ShellSplitTest(unittest.TestCase):
    def test_regular_commands(self):
        self.assertEqual([], sut.shell_split(""))
        self.assertEqual(["clang", "-c", "file.c"], sut.shell_split("clang -c file.c"))
        self.assertEqual(["clang", "-c", "file.c"], sut.shell_split("clang  -c  file.c"))
        self.assertEqual(["clang", "-c", "file.c"], sut.shell_split("clang -c\tfile.c"))

    def test_quoted_commands(self):
        self.assertEqual(["clang", "-c", "file.c"], sut.shell_split('"clang" -c "file.c"'))
        self.assertEqual(["clang", "-c", "file.c"], sut.shell_split("'clang' -c 'file.c'"))

    def test_shell_escaping(self):
        self.assertEqual(["clang", "-c", "file.c", "-Dv=space value"], sut.shell_split(r'clang -c file.c -Dv="space value"'))
        self.assertEqual(["clang", "-c", "file.c", '-Dv="quote'], sut.shell_split(r"clang -c file.c -Dv=\"quote"))
        self.assertEqual(["clang", "-c", "file.c", "-Dv=(word)"], sut.shell_split(r"clang -c file.c -Dv=\(word\)"))


class RunCommandTest(unittest.TestCase):
    def test_output_is_not_valid_utf8(self):
        cmd = [sys.executable, "-c", r"import sys; sys.stdout.buffer.write(b'\xff\xfe warning')"]
        output = sut.run_command(cmd)
        self.assertEqual(1, len(output))
        self.assertTrue(output[0].endswith(" warning"))

    def test_failing_command_output_is_not_valid_utf8(self):
        # the decode error shall not replace the real error
        cmd = [sys.executable, "-c", r"import sys; sys.stdout.buffer.write(b'\xff error'); sys.exit(2)"]
        with self.assertRaises(subprocess.CalledProcessError) as ctx:
            sut.run_command(cmd)
        self.assertEqual(2, ctx.exception.returncode)
        self.assertEqual(1, len(ctx.exception.output))
        self.assertTrue(ctx.exception.output[0].endswith(" error"))
