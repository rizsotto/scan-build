.. image:: https://img.shields.io/pypi/v/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://img.shields.io/pypi/l/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://img.shields.io/pypi/dm/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://img.shields.io/pypi/pyversions/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build


clanganalyzer
=============

``clanganalyzer`` runs the Clang static analyzer against a project using
its `compilation database`_, and generates a report of the potential bugs
it found. It lets you analyze an existing code base without modifying the
build.


History
-------

This project started as a Python rewrite of the ``scan-build`` Perl scripts
shipped with Clang. An earlier version was contributed to the Clang
repository as ``scan-build-py``, and this project has been published on PyPI
under the name `scan-build`_ ever since — which is why the package name and
the command name differ.

Up to version 2.x the package also provided ``intercept-build``, a tool to
capture compiler calls and produce a compilation database. That
functionality was removed in version 3.0: the `Bear`_ project now covers
all targeted platforms (including Windows, which was the original reason
for the Python implementation), so this package focuses solely on running
the analyzer. To create a compilation database, use Bear or your build
system's native support.


How to get
----------

The package is on PyPI under the name `scan-build`_. Install it with pip::

    $ pip install scan-build

Or as a standalone tool with uv::

    $ uv tool install scan-build


Prerequisites
-------------

1. **clang**, to compile the sources and to run the static analyzer.
2. **python** interpreter (version 3.10 or later).
3. A **compilation database** (``compile_commands.json``) for your project.
   CMake can generate one with ``-DCMAKE_EXPORT_COMPILE_COMMANDS=ON``; for
   other build systems, use `Bear`_.


How to use
----------

A typical workflow with a CMake project::

    $ cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    $ clanganalyzer --cdb build/compile_commands.json --output report

This runs the analyzer against every entry of the compilation database and
writes an HTML report into a subdirectory of the output directory. By
default the compilation database is read from ``compile_commands.json`` in
the current directory, and reports are written under the system temp
directory.

Some commonly used options:

- ``--output <path>`` — where to put the analyzer reports.
- ``--status-bugs`` — exit with a non-zero status if potential bugs were
  found; useful in CI.
- ``--exclude <directory>`` — skip files in the given directory (e.g.
  third-party code); can be repeated.
- ``--plist``, ``--plist-html`` — emit machine-readable plist output
  instead of (or along with) HTML.

Use ``--help`` for the full list of options. The tool is also installed
under the alias ``analyze-build``, the name it had in earlier releases.


Portability
-----------

It has been tested on FreeBSD, GNU/Linux, macOS and Windows.


Development
-----------

To set up a development environment::

    $ git clone https://github.com/rizsotto/scan-build.git
    $ cd scan-build
    $ uv sync --all-extras

To run tests::

    $ uv run pytest tests/unit
    $ uv run lit -v tests/functional

To run linting and type checking::

    $ uv run ruff check .
    $ uv run ruff format .
    $ uv run ty check clanganalyzer


Problem reports
---------------

If you find a bug in this documentation or elsewhere in the program or would
like to propose an improvement, please use the project's `issue tracker`_.
Please describe the bug and where you found it. If you have a suggestion
how to fix it, include that as well. Patches are also welcome.


License
-------

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.txt for details.


.. _compilation database: https://clang.llvm.org/docs/JSONCompilationDatabase.html
.. _scan-build: https://pypi.python.org/pypi/scan-build
.. _Bear: https://github.com/rizsotto/Bear
.. _issue tracker: https://github.com/rizsotto/scan-build/issues
