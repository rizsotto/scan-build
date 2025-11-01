# SPDX-License-Identifier: MIT
"""This module is responsible for parsing compilation database entries."""

import json
import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from clanganalyzer import shell_split

__all__ = ["classify_source", "Compilation", "CompilationDatabase"]


@dataclass(frozen=True)
class CompilationEntry:
    """Represents a compilation database entry.

    Attributes:
        directory: Working directory for the compilation
        file: Source file path (relative to directory)
        arguments: List of compiler arguments
    """

    directory: str
    file: str
    arguments: list[str]

    @classmethod
    def from_db_entry(cls, entry: dict[str, Any]) -> "CompilationEntry":
        """Create CompilationEntry from compilation database entry."""
        directory = entry["directory"]
        file = entry["file"]

        # Handle both "command" (string) and "arguments" (list) formats
        if "command" in entry:
            arguments = shell_split(entry["command"])
        else:
            arguments = entry["arguments"]
            if not isinstance(arguments, list):
                arguments = [arguments]

        return cls(directory=directory, file=file, arguments=arguments)


@dataclass
class Compilation:
    """Represents a compilation of a single source file."""

    directory: str
    source: str
    compiler: str
    flags: list[str]

    @classmethod
    def from_entry(cls, entry: CompilationEntry) -> "Compilation":
        """Create compilation from a compilation database entry."""
        directory = os.path.normpath(entry.directory)
        source = entry.file if os.path.isabs(entry.file) else os.path.join(directory, entry.file)
        source = os.path.normpath(source)

        # Extract compiler and flags from arguments
        compiler, flags = cls._parse_arguments(entry.arguments)

        return cls(directory=directory, source=source, compiler=compiler, flags=flags)

    @staticmethod
    def _parse_arguments(arguments: list[str]) -> tuple[str, list[str]]:
        """Parse compiler arguments to extract compiler type and flags.

        Returns:
            Tuple of (compiler_type, flags) where compiler_type is "c" or "c++"
        """
        if not arguments:
            return "c", []

        # Determine compiler type from executable name
        executable = os.path.basename(arguments[0])
        if any(pattern in executable for pattern in ["c++", "cxx", "g++", "clang++"]):
            compiler_type = "c++"
        else:
            compiler_type = "c"

        # Return all arguments except the compiler executable as flags
        # The analyzer will reconstruct the command as needed
        return compiler_type, arguments[1:]

    def as_dict(self) -> dict[str, Any]:
        """Convert compilation to dictionary representation."""
        return {
            "source": self.source,
            "directory": self.directory,
            "compiler": self.compiler,
            "flags": self.flags,
        }


class CompilationDatabase:
    """Compilation database loader."""

    @staticmethod
    def load(filename: str) -> Iterable[Compilation]:
        """Load compilations from compilation database file.

        :param filename: Path to compilation database JSON file
        :returns: Iterator of Compilation objects
        """
        with open(filename) as handle:
            entries = json.load(handle)

        for entry_data in entries:
            entry = CompilationEntry.from_db_entry(entry_data)
            yield Compilation.from_entry(entry)

    @staticmethod
    def file_commonprefix(filename: str) -> str:
        """Create file prefix from a compilation database entries."""
        with open(filename) as handle:
            return _commonprefix(item["file"] for item in json.load(handle))


def _commonprefix(files: Iterator[str]) -> str:
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


def classify_source(filename: str, c_compiler: bool = True) -> str | None:
    """Classify source file names and returns the presumed language,
    based on the file name extension.

    :param filename:    the source file name
    :param c_compiler:  indicate that the compiler is a C compiler,
    :return: the language from file name extension."""

    mapping = {
        ".c": "c" if c_compiler else "c++",
        ".i": "c-cpp-output" if c_compiler else "c++-cpp-output",
        ".ii": "c++-cpp-output",
        ".m": "objective-c",
        ".mi": "objective-c-cpp-output",
        ".mm": "objective-c++",
        ".mii": "objective-c++-cpp-output",
        ".C": "c++",
        ".cc": "c++",
        ".CC": "c++",
        ".cp": "c++",
        ".cpp": "c++",
        ".cxx": "c++",
        ".c++": "c++",
        ".C++": "c++",
        ".txx": "c++",
    }

    __, extension = os.path.splitext(os.path.basename(filename))
    return mapping.get(extension)
