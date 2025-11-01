#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
"""This module is a collection of methods commonly used in this project."""

import functools
import logging
import os
import os.path
import re
import shlex
import subprocess
import sys
from collections.abc import Callable
from typing import Any


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


def _decode_subprocess_output(result: Any) -> str:
    """Decode subprocess output to string if needed.

    subprocess.check_output returns bytes or string depending on Python version.
    """
    if not isinstance(result, str):
        return result.decode("utf-8")
    return result


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
        output = subprocess.check_output(
            command,
            cwd=directory,
            stderr=subprocess.STDOUT,
        )
        return _decode_subprocess_output(output).splitlines()
    except subprocess.CalledProcessError as ex:
        ex.output = _decode_subprocess_output(ex.output).splitlines()
        raise


def reconfigure_logging(verbose_level: int) -> None:
    """Reconfigure logging level and format based on verbosity.

    Args:
        verbose_level: Number of `-v` flags received (0 means no change)
    """
    if verbose_level == 0:
        return

    root = logging.getLogger()

    # Calculate log level: more verbose means lower level
    level = max(logging.DEBUG, logging.WARNING - (10 * verbose_level))
    root.setLevel(level)

    # Choose format based on verbosity
    if verbose_level <= 3:
        fmt_string = "%(name)s: %(levelname)s: %(message)s"
    else:
        fmt_string = "%(name)s: %(levelname)s: %(funcName)s: %(message)s"

    # Replace existing handlers
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt_string))
    root.handlers = [handler]


def command_entry_point(function: Callable[[], int]) -> Callable[[], int]:
    """Decorator for command line entry points.

    Provides standard initialization, exception handling, and cleanup
    for command line tools.

    Args:
        function: Entry point function that returns an exit code

    Returns:
        Wrapped function with error handling and logging setup
    """

    @functools.wraps(function)
    def wrapper() -> int:
        """Execute function with proper housekeeping."""
        try:
            # Initialize logging
            logging.basicConfig(format="%(name)s: %(message)s", level=logging.WARNING, stream=sys.stdout)
            # Set logger name to executable name
            logging.getLogger().name = os.path.basename(sys.argv[0])

            return function()

        except KeyboardInterrupt:
            logging.warning("Keyboard interrupt")
            return 130  # Standard signal received exit code

        except (OSError, subprocess.CalledProcessError):
            logging.exception("Internal error.")
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.error("Please report this bug and attach the output to the bug report")
            else:
                logging.error("Please run this command again and turn on verbose mode (add '-vvvv' as argument).")
            return 64  # Internal error exit code

        finally:
            logging.shutdown()

    return wrapper
