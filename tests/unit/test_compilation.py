# SPDX-License-Identifier: MIT

import json
import os
import tempfile
import unittest

import clanganalyzer.compilation as sut


class CompilationEntryTest(unittest.TestCase):
    def test_from_db_entry_with_arguments(self):
        """Test parsing compilation database entry with 'arguments' field."""
        entry_data = {
            "directory": "/home/user/project",
            "file": "src/main.c",
            "arguments": ["gcc", "-c", "-Wall", "src/main.c"],
        }

        entry = sut.CompilationEntry.from_db_entry(entry_data)

        self.assertEqual(entry.directory, "/home/user/project")
        self.assertEqual(entry.file, "src/main.c")
        self.assertEqual(entry.arguments, ["gcc", "-c", "-Wall", "src/main.c"])

    def test_from_db_entry_with_command(self):
        """Test parsing compilation database entry with 'command' field."""
        entry_data = {"directory": "/home/user/project", "file": "src/main.cpp", "command": "g++ -c -std=c++17 src/main.cpp"}

        entry = sut.CompilationEntry.from_db_entry(entry_data)

        self.assertEqual(entry.directory, "/home/user/project")
        self.assertEqual(entry.file, "src/main.cpp")
        self.assertEqual(entry.arguments, ["g++", "-c", "-std=c++17", "src/main.cpp"])

    def test_from_db_entry_with_quoted_command(self):
        """Test parsing compilation database entry with quoted arguments in command."""
        entry_data = {
            "directory": "/home/user/project",
            "file": "src/test.c",
            "command": 'gcc -DVERSION="1.0.0" -c src/test.c',
        }

        entry = sut.CompilationEntry.from_db_entry(entry_data)

        self.assertEqual(entry.directory, "/home/user/project")
        self.assertEqual(entry.file, "src/test.c")
        self.assertEqual(entry.arguments, ["gcc", "-DVERSION=1.0.0", "-c", "src/test.c"])


class CompilationTest(unittest.TestCase):
    def test_c_compilation(self):
        """Test creation of C compilation from entry."""
        entry = sut.CompilationEntry(directory="/project", file="main.c", arguments=["gcc", "-Wall", "-O2", "main.c"])

        compilation = sut.Compilation.from_entry(entry)

        self.assertEqual(compilation.compiler, "c")
        self.assertEqual(compilation.flags, ["-Wall", "-O2", "main.c"])
        self.assertEqual(compilation.directory, "/project")
        self.assertEqual(compilation.source, "/project/main.c")

    def test_cpp_compilation(self):
        """Test creation of C++ compilation from entry."""
        entry = sut.CompilationEntry(
            directory="/project", file="main.cpp", arguments=["g++", "-std=c++17", "-Wall", "main.cpp"]
        )

        compilation = sut.Compilation.from_entry(entry)

        self.assertEqual(compilation.compiler, "c++")
        self.assertEqual(compilation.flags, ["-std=c++17", "-Wall", "main.cpp"])
        self.assertEqual(compilation.directory, "/project")
        self.assertEqual(compilation.source, "/project/main.cpp")

    def test_clang_cpp_compilation(self):
        """Test C++ detection with clang++."""
        entry = sut.CompilationEntry(directory="/project", file="test.cc", arguments=["clang++", "-O3", "test.cc"])

        compilation = sut.Compilation.from_entry(entry)

        self.assertEqual(compilation.compiler, "c++")
        self.assertEqual(compilation.flags, ["-O3", "test.cc"])

    def test_absolute_file_path(self):
        """Test handling of absolute file paths."""
        entry = sut.CompilationEntry(directory="/project", file="/absolute/path/to/file.c", arguments=["gcc", "file.c"])

        compilation = sut.Compilation.from_entry(entry)

        self.assertEqual(compilation.source, "/absolute/path/to/file.c")

    def test_empty_arguments(self):
        """Test handling of empty arguments list."""
        entry = sut.CompilationEntry(directory="/project", file="empty.c", arguments=[])

        compilation = sut.Compilation.from_entry(entry)

        self.assertEqual(compilation.compiler, "c")
        self.assertEqual(compilation.flags, [])

    def test_equality(self):
        """Test compilation equality comparison."""
        entry1 = sut.CompilationEntry("/project", "main.c", ["gcc", "main.c"])
        entry2 = sut.CompilationEntry("/project", "main.c", ["gcc", "main.c"])
        entry3 = sut.CompilationEntry("/project", "other.c", ["gcc", "other.c"])

        comp1 = sut.Compilation.from_entry(entry1)
        comp2 = sut.Compilation.from_entry(entry2)
        comp3 = sut.Compilation.from_entry(entry3)

        self.assertEqual(comp1, comp2)
        self.assertNotEqual(comp1, comp3)
        self.assertNotEqual(comp1, "not a compilation")

    def test_as_dict(self):
        """Test conversion to dictionary."""
        entry = sut.CompilationEntry(directory="/project", file="main.c", arguments=["gcc", "-Wall", "main.c"])

        compilation = sut.Compilation.from_entry(entry)
        result = compilation.as_dict()

        expected = {"source": "/project/main.c", "directory": "/project", "compiler": "c", "flags": ["-Wall", "main.c"]}

        self.assertEqual(result, expected)


class CompilationDatabaseTest(unittest.TestCase):
    def test_load_simple_database(self):
        """Test loading a simple compilation database."""
        database_content = [
            {"directory": "/project", "file": "main.c", "arguments": ["gcc", "-c", "main.c"]},
            {"directory": "/project", "file": "utils.cpp", "command": "g++ -std=c++11 -c utils.cpp"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(database_content, f)
            temp_path = f.name

        try:
            compilations = list(sut.CompilationDatabase.load(temp_path))

            self.assertEqual(len(compilations), 2)

            # Check first compilation (C)
            comp1 = compilations[0]
            self.assertEqual(comp1.compiler, "c")
            self.assertEqual(comp1.source, "/project/main.c")
            self.assertEqual(comp1.flags, ["-c", "main.c"])

            # Check second compilation (C++)
            comp2 = compilations[1]
            self.assertEqual(comp2.compiler, "c++")
            self.assertEqual(comp2.source, "/project/utils.cpp")
            self.assertEqual(comp2.flags, ["-std=c++11", "-c", "utils.cpp"])

        finally:
            os.unlink(temp_path)

    def test_load_empty_database(self):
        """Test loading an empty compilation database."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_path = f.name

        try:
            compilations = list(sut.CompilationDatabase.load(temp_path))
            self.assertEqual(len(compilations), 0)
        finally:
            os.unlink(temp_path)


class SourceClassifierTest(unittest.TestCase):
    def test_sources(self):
        """Test source file classification by extension."""
        tests = [
            ("header.h", None),
            ("impl.c", "c"),
            ("impl.cc", "c++"),
            ("impl.cpp", "c++"),
            ("impl.cxx", "c++"),
            ("impl.C", "c++"),
            ("impl.c++", "c++"),
            ("preprocessed.i", "c-cpp-output"),
            ("preprocessed.ii", "c++-cpp-output"),
            ("objc.m", "objective-c"),
            ("objcpp.mm", "objective-c++"),
            ("template.txx", "c++"),
            ("unknown.xyz", None),
        ]

        for filename, expected in tests:
            with self.subTest(filename=filename):
                result = sut.classify_source(filename)
                self.assertEqual(result, expected)

    def test_c_compiler_context(self):
        """Test source classification with C compiler context."""
        # With C compiler context, .i files are C preprocessed output
        result = sut.classify_source("test.i", c_compiler=True)
        self.assertEqual(result, "c-cpp-output")

        # With C++ compiler context, .i files are C++ preprocessed output
        result = sut.classify_source("test.i", c_compiler=False)
        self.assertEqual(result, "c++-cpp-output")

        # .c files change meaning based on compiler context
        result = sut.classify_source("test.c", c_compiler=True)
        self.assertEqual(result, "c")

        result = sut.classify_source("test.c", c_compiler=False)
        self.assertEqual(result, "c++")


class CommonPrefixTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(sut._commonprefix([]), "")

    @unittest.skipIf(os.name == "nt", "windows has different path patterns")
    def test_with_different_filenames(self):
        self.assertEqual(sut._commonprefix(["/tmp/a.c", "/tmp/b.c"]), "/tmp")

    @unittest.skipIf(os.name == "nt", "windows has different path patterns")
    def test_with_different_dirnames(self):
        self.assertEqual(sut._commonprefix(["/tmp/abs/a.c", "/tmp/ack/b.c"]), "/tmp")

    @unittest.skipIf(os.name == "nt", "windows has different path patterns")
    def test_no_common_prefix(self):
        self.assertEqual(sut._commonprefix(["/tmp/abs/a.c", "/usr/ack/b.c"]), "/")

    @unittest.skipIf(os.name == "nt", "windows has different path patterns")
    def test_with_single_file(self):
        self.assertEqual(sut._commonprefix(["/tmp/a.c"]), "/tmp")

    @unittest.skipIf(os.name != "nt", "windows has different path patterns")
    def test_with_different_filenames_on_windows(self):
        self.assertEqual(sut._commonprefix(["c:\\tmp\\a.c", "c:\\tmp\\b.c"]), "c:\\tmp")

    @unittest.skipIf(os.name != "nt", "windows has different path patterns")
    def test_with_different_dirnames_on_windows(self):
        self.assertEqual(sut._commonprefix(["c:\\tmp\\abs\\a.c", "c:\\tmp\\ack\\b.c"]), "c:\\tmp")

    @unittest.skipIf(os.name != "nt", "windows has different path patterns")
    def test_no_common_prefix_on_windows(self):
        self.assertEqual(sut._commonprefix(["z:\\tmp\\abs\\a.c", "z:\\usr\\ack\\b.c"]), "z:\\")

    @unittest.skipIf(os.name != "nt", "windows has different path patterns")
    def test_different_drive_on_windows(self):
        self.assertEqual(sut._commonprefix(["c:\\tmp\\abs\\a.c", "z:\\usr\\ack\\b.c"]), "")

    @unittest.skipIf(os.name != "nt", "windows has different path patterns")
    def test_with_single_file_on_windows(self):
        self.assertEqual(sut._commonprefix(["z:\\tmp\\a.c"]), "z:\\tmp")


class CommonPrefixFromTest(unittest.TestCase):
    def test_commonprefix_from(self):
        """Test commonprefix_from with a compilation database file."""
        database_content = [
            {"directory": "/project", "file": "/project/src/main.c"},
            {"directory": "/project", "file": "/project/src/utils.c"},
            {"directory": "/project", "file": "/project/include/header.h"},
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(database_content, f)
            temp_path = f.name

        try:
            result = sut.CompilationDatabase.file_commonprefix(temp_path)
            self.assertEqual(result, "/project")
        finally:
            os.unlink(temp_path)

    def test_commonprefix_from_empty_database(self):
        """Test commonprefix_from with an empty compilation database."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_path = f.name

        try:
            result = sut.CompilationDatabase.file_commonprefix(temp_path)
            self.assertEqual(result, "")
        finally:
            os.unlink(temp_path)
