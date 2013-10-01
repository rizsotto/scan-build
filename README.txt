                                =========
                                Build EYE
                                =========

What is it?
-----------

It's a static analyzer wrapper for `Clang <http://clang.llvm.org/>`_. Instead
of using ``scan-build`` which does running the build and create the report.
Beye does use the `compilation database
<http://clang.llvm.org/docs/JSONCompilationDatabase.html>`_ and does only
the report generation.

One option to generate the compilation database file you could use `Bear
<https://github.com/rizsotto/Bear>`_ if you are using Linux, FreeBSD or OS X.

How to get
----------

Will be available soon from `the Python Package Index
<https://pypi.python.org/pypi>`_.

How to build
------------

::
    $ python setup.py build
    $ python setup.py install


How to use
----------

::
    $ beye

