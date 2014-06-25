
                                Build EYE
                                =========

What is it?
-----------

It's a static analyzer wrapper for `Clang <http://clang.llvm.org/>`_.
The original ``scan-build`` and ``ccc-analyzer`` are written in Perl.
This package contains reimplementation of those scripts in Python.
The reimplementation diverge from the original scripts in a few places.

In current state only the ``ccc-analyzer`` had been rewritten. The
``beye`` program is a copy of ``scan-build``.

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

::
    $ beye make


Or the same way as you would run the ``scan-build`` command.


Known problems
--------------

In the current state, it will complain about the not found ``clang``
executable. You need pass ``--use-analyzer`` and the location of
``clang`` executable to run it. Then it will work, but report that
it could have not copy the ``scanview.css`` and ``sorttable.js`` files
to the report directory.

These issues are exists because of the hybrid model. (Since ``beye`` is
still a Perl script instead of a Python.) When that job is also done,
these symptomes will hopefuly go away.
