[![Build Status](https://travis-ci.org/rizsotto/Beye.svg?branch=master)](https://travis-ci.org/rizsotto/Beye)

Build EYE
=========

It's a static analyzer wrapper for [Clang][CLANG]. The original `scan-build`
is written in Perl. This package contains reimplementation of that scripts
in Python. The reimplementation diverge from the original scripts in a few
places.

  [CLANG]: http://clang.llvm.org/

How to get
----------

Will be available soon from [the Python Package Index][PyPI].

  [PyPI]: https://pypi.python.org/pypi

How to build
------------

Should be quite portable on UNIX operating systems. It has been tested on
FreeBSD, GNU/Linux and OS X.

### Prerequisites

1. **clang compiler**, to compile the sources and have the static analyzer.
2. **python** interpreter (version 2.7, 3.2, 3.3, 3.4, 3.5).

### Build commands (optional)

This step is optional. Only in cases when you want to make a package,
run the test harness or just want an isolated python environment.

Please consider to use `virtualenv` or other tool to set up the working
environment.

    $ python setup.py build
    $ python setup.py install
    $ python setup.py test


How to use
----------

To run the Clang static analyzer against a project goes like this:

    $ scan-build <your build command>

To generate a compilation database file (compilation database is a JSON
file described [here][JCDB]) goes like this: 

    $ intercept-build intercept <your build command>

Use `--help` to know more about the commands.

  [JCDB]: http://clang.llvm.org/docs/JSONCompilationDatabase.html

Known problems
--------------

Because it uses `LD_PRELOAD` or `DYLD_INSERT_LIBRARIES` environment variables,
it does not append to it, but overrides it. So builds which are using these
variables might not work. (I don't know any build tool which does that, but
please let me know if you do.)

Problem reports
---------------
If you find a bug in this documentation or elsewhere in the program or would
like to propose an improvement, please use the project's [github issue
tracker][ISSUES]. Please describing the bug and where you found it. If you
have a suggestion how to fix it, include that as well. Patches are also
welcome.

  [ISSUES]: https://github.com/rizsotto/Beye/issues
