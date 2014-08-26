
                                Build EYE
                                =========

What is it?
-----------

It's a static analyzer wrapper for `Clang <http://clang.llvm.org/>`_.
The original ``scan-build`` and ``ccc-analyzer`` are written in Perl.
This package contains reimplementation of those scripts in Python.
The reimplementation diverge from the original scripts in a few places.

How to get
----------

Will be available soon from `the Python Package Index
<https://pypi.python.org/pypi>`_.

How to build
------------

::
    $ python setup.py build
    $ python setup.py test
    $ python setup.py install


How to use
----------

To generate the bug reports you need to have a compilation database.
It's a JSON file well documented `here
<http://clang.llvm.org/docs/JSONCompilationDatabase.html>`_.

::
    $ beye

Known problems
--------------

