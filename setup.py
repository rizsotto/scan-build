#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='beye',
    version='0.1',
    author='László Nagy',
    author_email='rizsotto@gmail.com',
    keywords=['clang', 'scan-build', 'checker', 'analyzer', 'static analyzer'],
    scripts=['bin/beye', 'bin/analyzer.py', 'bin/ccc-analyzer', 'bin/c++-analyzer'],
    url='https://github.com/rizsotto/Beye',
    license='LICENSE.txt',
    description='static code analyzer wrapper for Clang.',
    long_description=open('README.txt').read()
)
