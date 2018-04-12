#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='scan-build',
    version='2.0.12',
    author='László Nagy',
    author_email='rizsotto@gmail.com',
    keywords=['Clang', 'scan-build', 'static analyzer'],
    url='https://github.com/rizsotto/scan-build',
    license='LICENSE.txt',
    description='static code analyzer wrapper for Clang.',
    long_description=open('README.rst').read(),
    zip_safe=False,
    install_requires=['typing'],
    packages=['libscanbuild', 'libear'],
    package_data={'libscanbuild': ['resources/*'],
                  'libear': ['config.h.in', 'ear.c']},
    entry_points={
        'console_scripts': [
            'scan-build = libscanbuild.analyze:scan_build',
            'analyze-build = libscanbuild.analyze:analyze_build',
            'analyze-cc = libscanbuild.analyze:analyze_compiler_wrapper',
            'analyze-c++ = libscanbuild.analyze:analyze_compiler_wrapper',
            'intercept-build = libscanbuild.intercept:intercept_build',
            'intercept-cc = libscanbuild.intercept:intercept_compiler_wrapper',
            'intercept-c++ = libscanbuild.intercept:intercept_compiler_wrapper'
        ]
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: University of Illinois/NCSA Open Source License",
        "Environment :: Console", "Operating System :: POSIX",
        "Operating System :: MacOS :: MacOS X",
        "Intended Audience :: Developers", "Programming Language :: C",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Quality Assurance"
    ])
