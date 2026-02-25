.. image:: https://img.shields.io/pypi/v/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://img.shields.io/pypi/l/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://img.shields.io/pypi/dm/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://img.shields.io/pypi/pyversions/scan-build.svg
       :target: https://pypi.python.org/pypi/scan-build

.. image:: https://badges.gitter.im/rizsotto/scan-build.svg
        :target: https://gitter.im/rizsotto/scan-build?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge


clanganalyzer
=============

A package designed to run the clang static analyzer against projects
with existing compilation databases. The clanganalyzer tool runs the
clang static analyzer against a compilation database.


How to get
----------

It's available from `the Python Package Index`_ and can be installed using pip or uv::

    $ pip install scan-build

Or using uv (recommended)::

    $ uv add scan-build

For development::

    $ uv sync --all-extras


Portability
-----------

Should be working on UNIX operating systems.

- It has been tested on FreeBSD, GNU/Linux, OS X and Windows.


Prerequisites
-------------

1. **clang compiler**, to compile the sources and have the static analyzer.
2. **python** interpreter (version 3.10 or later). Supported versions: 3.10, 3.11, 3.12, 3.13.


How to use
----------

To run the Clang static analyzer against a project with an existing
compilation database goes like this::

    $ clanganalyzer

Use ``--help`` to know more about the command.


Prerequisites
-------------

The ``clanganalyzer`` tool requires:

1. An existing compilation database (``compile_commands.json``) for your project
2. The clang static analyzer to be available on your system

You can generate a compilation database using various tools like CMake
(with ``-DCMAKE_EXPORT_COMPILE_COMMANDS=ON``), Bear, or other build systems
that support compilation database generation.


Known problems
--------------

The tool requires a valid compilation database to function. If your project
doesn't have one, you'll need to generate it first using your build system
or tools like Bear.


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
    $ uv run ty clanganalyzer

Problem reports
---------------

If you find a bug in this documentation or elsewhere in the program or would
like to propose an improvement, please use the project's `issue tracker`_.
Please describe the bug and where you found it. If you have a suggestion
how to fix it, include that as well. Patches are also welcome.


License
-------

The project is licensed under University of Illinois/NCSA Open Source License.
See LICENSE.TXT for details.


.. _compilation database: http://clang.llvm.org/docs/JSONCompilationDatabase.html
.. _the Python Package Index: https://pypi.python.org/pypi/scan-build
.. _issue tracker: https://github.com/rizsotto/scan-build/issues
