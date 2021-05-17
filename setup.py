#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name='scan-build',
    version='2.0.20',
    author='László Nagy',
    author_email='rizsotto@gmail.com',
    keywords=['Clang', 'scan-build', 'static analyzer'],
    url='https://github.com/rizsotto/scan-build',
    license='LICENSE.txt',
    description='static code analyzer wrapper for Clang.',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    zip_safe=False,
    python_requires=">=3.6",
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
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Quality Assurance"
    ]
)
