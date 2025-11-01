#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
"""This module is a collection of methods commonly used in this project."""

import logging
import os
import os.path
import re
import shlex
import subprocess


def _unescape_shell_arg(arg: str) -> str:
    """Remove escaping characters from a shell argument.

    Handles both quoted strings and escaped characters in shell arguments.
    """
    if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] == '"':
        return re.sub(r'\\(["\\])', r"\1", arg[1:-1])
    return re.sub(r"\\([\\ $%&\(\)\[\]\{\}\*|<>@?!])", r"\1", arg)


def shell_split(string: str) -> list[str]:
    """Split a command string into arguments and unescape them.

    Args:
        string: Command string to split

    Returns:
        List of unescaped command arguments
    """
    return [_unescape_shell_arg(token) for token in shlex.split(string)]


def run_command(command: list[str], cwd: str | None = None) -> list[str]:
    """Run a command and return its output as lines.

    Args:
        command: Command as a list of arguments
        cwd: Working directory for command execution (defaults to current directory)

    Returns:
        Command output split into lines

    Raises:
        subprocess.CalledProcessError: If command execution fails
    """
    try:
        directory = os.path.abspath(cwd) if cwd else os.getcwd()
        logging.debug("exec command %s in %s", command, directory)
        output: bytes = subprocess.check_output(
            command,
            cwd=directory,
            stderr=subprocess.STDOUT,
        )
        return output.decode("utf-8").splitlines()
    except subprocess.CalledProcessError as ex:
        ex.output = ex.output.decode("utf-8").splitlines()
        raise
