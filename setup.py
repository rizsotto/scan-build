#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='scan-build',
    version='1.2',
    author='László Nagy',
    author_email='rizsotto@gmail.com',
    keywords=['Clang', 'scan-build', 'static analyzer'],
    url='https://github.com/rizsotto/scan-build',
    license='LICENSE.txt',
    description='static code analyzer wrapper for Clang.',
    long_description=open('README.rst').read(),
    zip_safe=False,
    scripts=['bin/scan-build',
             'bin/intercept-build', 'bin/intercept-cc', 'bin/intercept-c++',
             'bin/analyze-build', 'bin/analyze-cc', 'bin/analyze-c++'],
    packages=['libscanbuild', 'libear'],
    package_data={'libscanbuild': ['resources/*'], 'libear': ['config.h.in', 'ear.c']},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: University of Illinois/NCSA Open Source License",
        "Environment :: Console",
        "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Intended Audience :: Developers",
        "Programming Language :: C",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Quality Assurance"
    ]
)
