[![Build Status](https://travis-ci.org/rizsotto/scan-build.svg?branch=master)](https://travis-ci.org/rizsotto/scan-build)

# scan-build

It's a static analyzer wrapper for [Clang][CLANG]. The original `scan-build`
is written in Perl. This package contains reimplementation of that scripts
in Python. The reimplementation diverge from the original scripts in a few
places.


## How to get

It's available from [the Python Package Index][PyPI].

    $ pip install scan-build

Or check out the sources and add the directory `bin` to your `PATH` environment.


## Portability

Should be working on UNIX operating systems.

* It has been tested on FreeBSD, GNU/Linux and OS X.
* Prepared to work on windows, but need help to make it.


## Prerequisites

1. **clang compiler**, to compile the sources and have the static analyzer.
2. **python** interpreter (version 2.7, 3.2, 3.3, 3.4, 3.5).


## How to use

To run the Clang static analyzer against a project goes like this:

    $ scan-build <your build command>

To generate a compilation database file (compilation database is a JSON
file described [here][JCDB]) goes like this: 

    $ intercept-build <your build command>

To run the Clang static analyzer against a project with compilation database
goes like this:

    $ analyze-build --cdb <compilation database json file>

Use `--help` to know more about the commands.


## Known problems

Because it uses `LD_PRELOAD` or `DYLD_INSERT_LIBRARIES` environment variables,
it does not append to it, but overrides it. So builds which are using these
variables might not work. (I don't know any build tool which does that, but
please let me know if you do.)


## Problem reports

If you find a bug in this documentation or elsewhere in the program or would
like to propose an improvement, please use the project's [issue tracker][ISSUES].
Please describing the bug and where you found it. If you have a suggestion
how to fix it, include that as well. Patches are also welcome.

  [CLANG]: http://clang.llvm.org/
  [PyPI]: https://pypi.python.org/pypi
  [JCDB]: http://clang.llvm.org/docs/JSONCompilationDatabase.html
  [ISSUES]: https://github.com/rizsotto/scan-build/issues
