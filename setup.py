#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from subprocess import check_call
from distutils.dir_util import mkpath
from distutils.command.build import build
from distutils.command.install import install


class BuildEAR(build):

    def run(self):
        import os
        import os.path

        mkpath(self.build_temp)

        source_dir = os.path.join(os.getcwd(), 'libear')
        dest_dir = os.path.abspath(self.build_lib)

        cmd = ['cmake', '-DCMAKE_INSTALL_PREFIX=' + dest_dir, source_dir]
        check_call(cmd, cwd=self.build_temp)

        cmd = ['make', 'install']
        check_call(cmd, cwd=self.build_temp)


class Build(build):

    def run(self):
        self.run_command('buildear')
        build.run(self)


class Install(install):

    def run(self):
        self.run_command('build')
        self.run_command('install_scripts')
        install.run(self)


setup(
    name='beye',
    version='0.1',
    author='László Nagy',
    author_email='rizsotto@gmail.com',
    keywords=['clang', 'scan-build', 'analyzer', 'static analyzer'],
    url='https://github.com/rizsotto/Beye',
    license='LICENSE.txt',
    description='static code analyzer wrapper for Clang.',
    long_description=open('README.md').read(),
    zip_safe=False,
    scripts=['bin/scan-build'],
    packages=['analyzer'],
    package_data={'analyzer': ['resources/*']},
    cmdclass={'buildear': BuildEAR, 'install': Install, 'build': Build},
    classifiers=[
        "Development Status :: 4 - Beta",
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
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Quality Assurance"
    ],
    test_suite="tests.suite"
)
