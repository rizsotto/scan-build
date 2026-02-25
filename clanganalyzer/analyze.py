# SPDX-License-Identifier: MIT
"""This module implements the 'clanganalyzer' command API.

To run the static analyzer against a project goes like this:

 -- Analyze:   run the analyzer against the compilation database,
 -- Report:    create a cover report from the analyzer outputs."""

import argparse
import contextlib
import datetime
import functools
import logging
import multiprocessing
import os
import os.path
import platform
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Generator, Iterable
from typing import Any

from clanganalyzer import run_command
from clanganalyzer.arguments import parse_args
from clanganalyzer.clang import get_arguments, get_version
from clanganalyzer.compilation import Compilation, CompilationDatabase, classify_source
from clanganalyzer.config import get_disabled_architectures, get_ignored_flags, get_supported_languages
from clanganalyzer.report import document

__all__ = ["analyze_build"]


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


@command_entry_point
def analyze_build() -> int:
    """Entry point for clanganalyzer command."""

    args = parse_args()
    # will re-assign the report directory as new output
    with report_directory(args.output, args.keep_empty) as args.output:
        # run the analyzer against a compilation db
        compilations = CompilationDatabase.load(args.cdb)
        run_analyzer_parallel(compilations, args)
        # cover report generation and bug counting
        number_of_bugs = document(args)
        # set exit status as it was requested
        return number_of_bugs if args.status_bugs else 0


def analyze_parameters(args: argparse.Namespace) -> dict[str, Any]:
    """Mapping between the command line parameters and the analyzer run
    method. The run method works with a plain dictionary, while the command
    line parameters are in a named tuple.
    The keys are very similar, and some values are preprocessed."""

    def prefix_with(constant: Any, pieces: list[Any]) -> list[Any]:
        """From a sequence create another sequence where every second element
        is from the original sequence and the odd elements are the prefix.

        eg.: prefix_with(0, [1,2,3]) creates [0, 1, 0, 2, 0, 3]"""

        return [elem for piece in pieces for elem in [constant, piece]]

    def direct_args(args: argparse.Namespace) -> list[str]:
        """A group of command line arguments can mapped to command
        line arguments of the analyzer."""

        result = []

        if args.store_model:
            result.append(f"-analyzer-store={args.store_model}")
        if args.constraints_model:
            result.append(f"-analyzer-constraints={args.constraints_model}")
        if args.internal_stats:
            result.append("-analyzer-stats")
        if args.analyze_headers:
            result.append("-analyzer-opt-analyze-headers")
        if args.stats:
            result.append("-analyzer-checker=debug.Stats")
        if args.maxloop:
            result.extend(["-analyzer-max-loop", str(args.maxloop)])
        if args.output_format:
            result.append(f"-analyzer-output={args.output_format}")
        if args.analyzer_config:
            result.extend(["-analyzer-config", args.analyzer_config])
        if args.verbose >= 4:
            result.append("-analyzer-display-progress")
        if args.plugins:
            result.extend(prefix_with("-load", args.plugins))
        if args.enable_checker:
            checkers = ",".join(args.enable_checker)
            result.extend(["-analyzer-checker", checkers])
        if args.disable_checker:
            checkers = ",".join(args.disable_checker)
            result.extend(["-analyzer-disable-checker", checkers])

        return prefix_with("-Xclang", result)

    return {
        "clang": args.clang,
        "output_dir": args.output,
        "output_format": args.output_format,
        "output_failures": args.output_failures,
        "direct_args": direct_args(args),
        "analyzer_target": args.analyzer_target,
        "force_debug": args.force_debug,
        "excludes": args.excludes,
    }


def _pool_initializer(verbose: int) -> None:
    """Initialize logging in pool worker processes.

    With the 'forkserver' multiprocessing start method (default on Python 3.12+),
    worker processes do not inherit the parent's logging configuration. This
    initializer reconfigures logging so that debug output from workers is visible.
    """
    from clanganalyzer.arguments import reconfigure_logging

    reconfigure_logging(verbose)


def run_analyzer_parallel(compilations: Iterable[Compilation], args: argparse.Namespace) -> None:
    """Runs the analyzer against the given compilations."""

    logging.debug("run analyzer against compilation database")
    consts = analyze_parameters(args)
    parameters = (dict(compilation.as_dict(), **consts) for compilation in compilations)
    # when verbose output requested execute sequentially
    pool = multiprocessing.Pool(
        1 if args.verbose > 2 else None,
        initializer=_pool_initializer,
        initargs=(args.verbose,),
    )
    for current in pool.imap_unordered(run, parameters):
        logging_analyzer_output(current)
    pool.close()
    pool.join()


@contextlib.contextmanager
def report_directory(hint: str, keep: bool) -> Generator[str, None, None]:
    """Responsible for the report directory.

    hint -- could specify the parent directory of the output directory.
    keep -- a boolean value to keep or delete the empty report directory."""

    stamp_format = "clanganalyzer-%Y-%m-%d-%H-%M-%S-%f-"
    stamp = datetime.datetime.now().strftime(stamp_format)
    parent_dir = os.path.abspath(hint)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    name = tempfile.mkdtemp(prefix=stamp, dir=parent_dir)

    logging.info("Report directory created: %s", name)

    try:
        yield name
    finally:
        if os.listdir(name):
            msg = f"Run 'scan-view {name}' to examine bug reports."
            keep = True
        else:
            if keep:
                msg = f"Report directory '{name}' contains no report, but kept."
            else:
                msg = f"Removing directory '{name}' because it contains no report."
        logging.warning(msg)

        if not keep:
            os.rmdir(name)


def require(required: list[str]) -> Callable:
    """Decorator for checking the required values in state.

    It checks the required attributes in the passed state and stop when
    any of those is missing."""

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for key in required:
                assert key in args[0], f"{key} is missing"
            return method(*args, **kwargs)

        return wrapper

    return decorator


@require(
    [
        "flags",  # entry from compilation
        "compiler",  # entry from compilation
        "directory",  # entry from compilation
        "source",  # entry from compilation
        "clang",  # clang executable name (and path)
        "direct_args",  # arguments from command line
        "excludes",  # list of directories
        "force_debug",  # kill non debug macros
        "output_dir",  # where generated report files shall go
        "output_format",  # it's 'plist', 'html', 'plist-html',
        # 'text' or 'plist-multi-file'
        "output_failures",
    ]
)  # generate crash reports or not
def run(opts: dict[str, Any]) -> dict[str, Any]:
    """Entry point to run (or not) static analyzer against a single entry
    of the compilation database.

    This complex task is decomposed into smaller methods which are calling
    each other in chain. If the analysis is not possible the given method
    just return and break the chain.

    The passed parameter is a python dictionary. Each method first check
    that the needed parameters received. (This is done by the 'require'
    decorator. It's like an 'assert' to check the contract between the
    caller and the called method.)"""

    command = [opts["compiler"], "-c"] + opts["flags"] + [opts["source"]]
    logging.debug("Run analyzer against '%s'", command)
    return exclude(opts)


def logging_analyzer_output(opts: dict[str, Any] | None) -> None:
    """Display error message from analyzer."""

    if opts and "error_output" in opts:
        for line in opts["error_output"]:
            logging.info(line)


@require(["clang", "directory", "flags", "source", "output_dir", "language", "error_output", "exit_code"])
def report_failure(opts: dict[str, Any]) -> None:
    """Create report when analyzer failed.

    The major report is the preprocessor output. The output filename generated
    randomly. The compiler output also captured into '.stderr.txt' file.
    And some more execution context also saved into '.info.txt' file."""

    def extension() -> str:
        """Generate preprocessor file extension."""

        mapping = {"objective-c++": ".mii", "objective-c": ".mi", "c++": ".ii"}
        return mapping.get(opts["language"], ".i")

    def destination() -> str:
        """Creates failures directory if not exits."""

        failures_dir = os.path.join(opts["output_dir"], "failures")
        if not os.path.isdir(failures_dir):
            os.makedirs(failures_dir)
        return failures_dir

    # Classify error type: when Clang terminated by a signal it's a 'Crash'.
    # (python subprocess Popen.returncode is negative when child terminated
    # by signal.) Everything else is 'Other Error'.
    error = "crash" if opts["exit_code"] < 0 else "other_error"
    # Create preprocessor output file name. (This is blindly following the
    # Perl implementation.)
    (fd, name) = tempfile.mkstemp(suffix=extension(), prefix="clang_" + error + "_", dir=destination())
    os.close(fd)
    # Execute Clang again, but run the syntax check only.
    try:
        cwd = opts["directory"]
        cmd = get_arguments([opts["clang"], "-fsyntax-only", "-E"] + opts["flags"] + [opts["source"], "-o", name], cwd)
        run_command(cmd, cwd=cwd)
        # write general information about the crash
        with open(name + ".info.txt", "w") as handle:
            handle.write(opts["source"] + os.linesep)
            handle.write(error.title().replace("_", " ") + os.linesep)
            handle.write(" ".join(cmd) + os.linesep)
            handle.write(" ".join(platform.uname()) + os.linesep)
            handle.write(get_version(opts["clang"]))
            handle.close()
        # write the captured output too
        with open(name + ".stderr.txt", "w") as handle:
            for line in opts["error_output"]:
                handle.write(line)
            handle.close()
    except (OSError, subprocess.CalledProcessError):
        logging.warning("failed to report failure", exc_info=True)


@require(["clang", "directory", "flags", "direct_args", "source", "output_dir", "output_format"])
def run_analyzer(opts: dict[str, Any], continuation: Callable[[dict[str, Any]], None] = report_failure) -> dict[str, Any]:
    """It assembles the analysis command line and executes it. Capture the
    output of the analysis and returns with it. If failure reports are
    requested, it calls the continuation to generate it."""

    def target() -> str:
        """Creates output file name for reports."""
        if opts["output_format"].startswith("plist"):
            (handle, name) = tempfile.mkstemp(prefix="report-", suffix=".plist", dir=opts["output_dir"])
            os.close(handle)
            return name
        return opts["output_dir"]

    try:
        cwd = opts["directory"]
        cmd = get_arguments(
            [opts["clang"], "--analyze"] + opts["direct_args"] + opts["flags"] + [opts["source"], "-o", target()], cwd
        )
        output = run_command(cmd, cwd=cwd)
        return {"error_output": output, "exit_code": 0}
    except OSError:
        message = f'failed to execute "{opts["clang"]}"'
        return {"error_output": [message], "exit_code": 127}
    except subprocess.CalledProcessError as ex:
        logging.warning("analysis failed", exc_info=True)
        result = {"error_output": ex.output, "exit_code": ex.returncode}
        if opts.get("output_failures", False):
            opts.update(result)
            continuation(opts)
        return result


@require(["flags", "force_debug"])
def filter_debug_flags(
    opts: dict[str, Any], continuation: Callable[[dict[str, Any]], dict[str, Any]] = run_analyzer
) -> dict[str, Any]:
    """Filter out nondebug macros when requested."""

    if opts.pop("force_debug"):
        # lazy implementation just append an undefine macro at the end
        opts.update({"flags": opts["flags"] + ["-UNDEBUG"]})

    return continuation(opts)


@require(["language", "compiler", "source", "flags"])
def language_check(
    opts: dict[str, Any], continuation: Callable[[dict[str, Any]], dict[str, Any]] = filter_debug_flags
) -> dict[str, Any]:
    """Find out the language from command line parameters or file name
    extension. The decision also influenced by the compiler invocation."""

    accepted = get_supported_languages()

    # language can be given as a parameter...
    language = opts.pop("language")
    compiler = opts.pop("compiler")
    # ... or find out from source file extension
    if language is None and compiler is not None:
        language = classify_source(opts["source"], compiler == "c")

    if language is None:
        logging.debug("skip analysis, language not known")
        return {}
    elif language not in accepted:
        logging.debug("skip analysis, language not supported")
        return {}

    logging.debug("analysis, language: %s", language)
    opts.update({"language": language, "flags": ["-x", language] + opts["flags"]})
    return continuation(opts)


@require(["arch_list", "flags"])
def arch_check(
    opts: dict[str, Any], continuation: Callable[[dict[str, Any]], dict[str, Any]] = language_check
) -> dict[str, Any]:
    """Do run analyzer through one of the given architectures."""

    disabled = get_disabled_architectures()

    received_list = opts.pop("arch_list")
    if received_list:
        # filter out disabled architectures and -arch switches
        filtered_list = [a for a in received_list if a not in disabled]
        if filtered_list:
            # There should be only one arch given (or the same multiple
            # times). If there are multiple arch are given and are not
            # the same, those should not change the pre-processing step.
            # But that's the only pass we have before run the analyzer.
            current = filtered_list.pop()
            logging.debug("analysis, on arch: %s", current)

            opts.update({"flags": ["-arch", current] + opts["flags"]})
            return continuation(opts)
        logging.debug("skip analysis, found not supported arch")
        return {}
    logging.debug("analysis, on default arch")
    return continuation(opts)


@require(["analyzer_target", "flags"])
def target_check(
    opts: dict[str, Any], continuation: Callable[[dict[str, Any]], dict[str, Any]] = arch_check
) -> dict[str, Any]:
    """Do run analyzer through the given target triple"""

    target = opts.pop("analyzer_target")
    if target is not None:
        opts.update({"flags": ["-target", target] + opts["flags"]})
        logging.debug("analysis, target triple is %s", target)
    else:
        logging.debug("analysis, default target triple")
    return continuation(opts)


@require(["flags"])
def classify_parameters(
    opts: dict[str, Any], continuation: Callable[[dict[str, Any]], dict[str, Any]] = target_check
) -> dict[str, Any]:
    """Prepare compiler flags (filters some and add others) and take out
    language (-x) and architecture (-arch) flags for future processing."""

    # the result of the method
    result: dict[str, Any] = {
        "flags": [],  # the filtered compiler flags
        "arch_list": [],  # list of architecture flags
        "language": None,  # compilation language, None, if not specified
    }

    # iterate on the compile options
    args = iter(opts["flags"])
    for arg in args:
        # take arch flags into a separate basket
        if arg == "-arch":
            result["arch_list"].append(next(args))
        # take language
        elif arg == "-x":
            result["language"] = next(args)
        # ignore some flags
        elif arg in get_ignored_flags():
            count = get_ignored_flags()[arg]
            for _ in range(count):
                next(args)
        # we don't care about extra warnings, but we should suppress ones
        # that we don't want to see.
        elif re.match(r"^-W.+", arg) and not re.match(r"^-Wno-.+", arg):
            pass
        # and consider everything else as compilation flag.
        else:
            result["flags"].append(arg)

    opts.update(result)
    return continuation(opts)


@require(["source", "excludes"])
def exclude(
    opts: dict[str, Any], continuation: Callable[[dict[str, Any]], dict[str, Any]] = classify_parameters
) -> dict[str, Any]:
    """Analysis might be skipped, when one of the requested excluded
    directory contains the file."""

    def contains(directory: str, entry: str) -> bool:
        """Check is directory contains the given file."""

        # When a directory contains a file, then the relative path to the
        # file from that directory does not start with a parent dir prefix.
        relative = os.path.relpath(entry, directory).split(os.sep)
        return len(relative) > 0 and relative[0] != os.pardir

    if any(contains(entry, opts["source"]) for entry in opts["excludes"]):
        logging.debug("skip analysis, file requested to exclude")
        return {}
    return continuation(opts)
