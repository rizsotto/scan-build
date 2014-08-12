#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='beye',
    version='0.1',
    author='László Nagy',
    author_email='rizsotto@gmail.com',
    keywords=['clang', 'scan-build', 'analyzer', 'static analyzer'],
    url='https://github.com/rizsotto/Beye',
    license='LICENSE.txt',
    description='static code analyzer wrapper for Clang.',
    long_description=open('README.rst').read(),
    zip_safe=False,
    packages=find_packages(),
    package_data={'analyzer': ['resources/*']},
    entry_points={
        'console_scripts': [
            'beye = analyzer.beye:main'
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: University of Illinois/NCSA Open Source License",
        "Environment :: Console",
        "Operating System :: POSIX",
        "Intended Audience :: Developers",
        "Programming Language :: C",
        "Programming Language :: C++",
        "Programming Language :: Objective C",
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Quality Assurance"
    ],
    test_suite="tests.suite"
)
