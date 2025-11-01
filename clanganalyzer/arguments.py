#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
"""This module parses and validates arguments for command-line interfaces.

It uses argparse module to create the command line parser. (This library is
in the standard python library since 3.2 and backported to 2.7, but not
earlier.)

It also implements basic validation methods, related to the command.
Validations are mostly calling specific help methods, or mangling values.
"""

import argparse
import logging
import os
import sys
import tempfile

from clanganalyzer.clang import get_checkers


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


# Default values
DEFAULT_OUTPUT_DIR = tempfile.gettempdir()
DEFAULT_CDB_FILE = "compile_commands.json"

__all__ = ["parse_args_for_analyze_build"]


def parse_args_for_analyze_build() -> argparse.Namespace:
    """Parse and validate command-line arguments for clanganalyzer."""

    parser = create_analyze_parser()
    args = parser.parse_args()

    reconfigure_logging(args.verbose)
    logging.debug("Raw arguments %s", sys.argv)

    normalize_args_for_analyze(args)
    validate_args_for_analyze(parser, args)
    logging.debug("Parsed arguments: %s", args)
    return args


def normalize_args_for_analyze(args: argparse.Namespace) -> None:
    """Normalize parsed arguments for clanganalyzer.

    :param args: Parsed argument object. (Will be mutated.)"""

    # make plugins always a list. (it might be None when not specified.)
    if args.plugins is None:
        args.plugins = []

    # make exclude directory list unique and absolute.
    uniq_excludes = {os.path.abspath(entry) for entry in args.excludes}
    args.excludes = list(uniq_excludes)

    # flatten comma-separated lists for checker options
    if hasattr(args, "enable_checker") and args.enable_checker:
        flattened = []
        for item in args.enable_checker:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.extend(item.split(","))
        args.enable_checker = flattened

    if hasattr(args, "disable_checker") and args.disable_checker:
        flattened = []
        for item in args.disable_checker:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.extend(item.split(","))
        args.disable_checker = flattened


def validate_args_for_analyze(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Command line parsing is done by the argparse module, but semantic
    validation still needs to be done. This method is doing it for
    clanganalyzer commands.

    :param parser: The command line parser object.
    :param args: Parsed argument object.
    :return: No return value, but this call might throw when validation
    fails."""

    if args.help_checkers_verbose:
        print_checkers(get_checkers(args.clang, args.plugins))
        parser.exit(status=0)
    elif args.help_checkers:
        print_active_checkers(get_checkers(args.clang, args.plugins))
        parser.exit(status=0)
    elif not os.path.exists(args.cdb):
        parser.error(message="compilation database is missing")


def create_analyze_parser() -> argparse.ArgumentParser:
    """Creates a parser for command-line arguments to 'analyze'."""

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    _ = parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Enable verbose output from clanganalyzer. A second, third and fourth flags increases verbosity.",
    )
    _ = parser.add_argument("--cdb", metavar="<file>", default=DEFAULT_CDB_FILE, help="The JSON compilation database.")

    _ = parser.add_argument(
        "--status-bugs",
        action="store_true",
        help="The exit status of clanganalyzer is non-zero if potential bugs are found, zero otherwise.",
    )
    _ = parser.add_argument(
        "--exclude",
        metavar="<directory>",
        dest="excludes",
        action="append",
        default=[],
        help="Do not run static analyzer against files found in this directory. (You can specify this option multiple times.) Could be useful when project contains 3rd party libraries.",
    )

    output = parser.add_argument_group("output control options")
    _ = output.add_argument(
        "--output",
        "-o",
        metavar="<path>",
        default=DEFAULT_OUTPUT_DIR,
        help="Specifies the output directory for analyzer reports. Subdirectory will be created if default directory is targeted.",
    )
    _ = output.add_argument(
        "--keep-empty",
        action="store_true",
        help="Don't remove the build results directory even if no issues were reported.",
    )
    _ = output.add_argument(
        "--html-title",
        metavar="<title>",
        help="Specify the title used on generated HTML pages. If not specified, a default title will be used.",
    )
    format_group = output.add_mutually_exclusive_group()
    _ = format_group.add_argument(
        "--plist",
        dest="output_format",
        const="plist",
        default="html",
        action="store_const",
        help="Cause the results as a set of .plist files.",
    )
    _ = format_group.add_argument(
        "--plist-html",
        dest="output_format",
        const="plist-html",
        default="html",
        action="store_const",
        help="Cause the results as a set of .html and .plist files.",
    )
    _ = format_group.add_argument(
        "--plist-multi-file",
        dest="output_format",
        const="plist-multi-file",
        default="html",
        action="store_const",
        help="Cause the results as a set of .plist files with extra information on related files.",
    )
    # TODO: implement '-view '

    advanced = parser.add_argument_group("advanced options")
    _ = advanced.add_argument(
        "--use-analyzer",
        metavar="<path>",
        dest="clang",
        default="clang",
        help="clanganalyzer uses the 'clang' executable relative to itself for static analysis. One can override this behavior with this option by using the 'clang' packaged with Xcode (on OS X) or from the PATH.",
    )
    _ = advanced.add_argument(
        "--analyzer-target",
        dest="analyzer_target",
        metavar="<target triple name for analysis>",
        help="This provides target triple information to clang static analyzer. It only changes the target for analysis but doesn't change the target of a real compiler.",
    )
    _ = advanced.add_argument(
        "--no-failure-reports",
        dest="output_failures",
        action="store_false",
        help="Do not create a 'failures' subdirectory that includes analyzer crash reports and preprocessed source files.",
    )
    _ = parser.add_argument(
        "--analyze-headers",
        action="store_true",
        help="Also analyze functions in #included files. By default, such functions are skipped unless they are called by functions within the main source file.",
    )
    _ = advanced.add_argument("--stats", action="store_true", help="Generates visitation statistics for the project.")
    _ = advanced.add_argument("--internal-stats", action="store_true", help="Generate internal analyzer statistics.")
    _ = advanced.add_argument(
        "--maxloop",
        metavar="<loop count>",
        type=int,
        help="Specify the number of times a block can be visited before giving up. Increase for more comprehensive coverage at a cost of speed.",
    )
    _ = advanced.add_argument(
        "--store",
        metavar="<model>",
        dest="store_model",
        choices=["region", "basic"],
        help="Specify the store model used by the analyzer. 'region' specifies a field-sensitive store model. 'basic' which is far less precise but can more quickly analyze code. 'basic' was the default store model for checker-0.221 and earlier.",
    )
    _ = advanced.add_argument(
        "--constraints",
        metavar="<model>",
        dest="constraints_model",
        choices=["range", "basic"],
        help="Specify the constraint engine used by the analyzer. Specifying 'basic' uses a simpler, less powerful constraint model used by checker-0.160 and earlier.",
    )
    _ = advanced.add_argument(
        "--analyzer-config",
        metavar="<options>",
        help="Provide options to pass through to the analyzer's -analyzer-config flag. Several options are separated with comma: 'key1=val1,key2=val2'. Available options: stable-report-filename=true or false (default). Switch the page naming to: report-<filename>-<function/method name>-<id>.html instead of report-XXXXXX.html",
    )
    _ = advanced.add_argument(
        "--force-analyze-debug-code",
        dest="force_debug",
        action="store_true",
        help="Tells analyzer to enable assertions in code even if they were disabled during compilation, enabling more precise results.",
    )

    plugins = parser.add_argument_group("checker options")
    _ = plugins.add_argument(
        "--load-plugin",
        metavar="<plugin library>",
        dest="plugins",
        action="append",
        help="Loading external checkers using the clang plugin interface.",
    )
    _ = plugins.add_argument(
        "--enable-checker",
        metavar="<checker name>",
        action="append",
        help="Enable specific checker. Supports comma-separated lists.",
    )
    _ = plugins.add_argument(
        "--disable-checker",
        metavar="<checker name>",
        action="append",
        help="Disable specific checker. Supports comma-separated lists.",
    )
    _ = plugins.add_argument(
        "--help-checkers",
        action="store_true",
        help="A default group of checkers is run unless explicitly disabled. Exactly which checkers constitute the default group is a function of the operating system in use. These can be printed with this flag.",
    )
    _ = plugins.add_argument(
        "--help-checkers-verbose", action="store_true", help="Print all available checkers and mark the enabled ones."
    )

    return parser


def print_active_checkers(checkers: dict[str, tuple[str, bool]]) -> None:
    """Print active checkers to stdout."""

    for name in sorted(name for name, (_, active) in checkers.items() if active):
        print(name)


def print_checkers(checkers: dict[str, tuple[str, bool]]) -> None:
    """Print verbose checker help to stdout."""

    print("")
    print("available checkers:")
    print("")
    for name in sorted(checkers.keys()):
        description, active = checkers[name]
        prefix = "+" if active else " "
        if len(name) > 30:
            print(f" {prefix} {name}")
            print(" " * 35 + description)
        else:
            print(f" {prefix} {name: <30}  {description}")
    print("")
    print('NOTE: "+" indicates that an analysis is enabled by default.')
    print("")
