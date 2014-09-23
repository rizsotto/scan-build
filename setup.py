#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from setuptools import Extension
from distutils.command.config import config
from distutils.command.build_ext import build_ext
from distutils.ccompiler import new_compiler


class CreateConfig(config):
    def finalize_options(self):
        self.compiler = new_compiler()
        self.compiler.define_macro('_GNU_SOURCE')
        self.dump_source=None
        self.verbose=None
        self.noisy=None

        self.defines = {
            'HAVE_DLOPEN': self.check_func(func='dlopen', headers=['dlfcn.h'], libraries=['dl']),
            'HAVE_DLSYM': self.check_func(func='dlsym', headers=['dlfcn.h'], libraries=['dl']),
            'HAVE_REALPATH': self.check_func(func='realpath', headers=['stdlib.h']),
            'HAVE_VFORK': self.check_func(func='vfork', headers=['unistd.h']),
            'HAVE_EXECVE': self.check_func(func='execve', headers=['unistd.h']),
            'HAVE_EXECV': self.check_func(func='execv', headers=['unistd.h']),
            'HAVE_EXECVPE': self.check_func(func='execvpe', headers=['unistd.h']),
            'HAVE_EXECVP': self.check_func(func='execvp', headers=['unistd.h']),
            'HAVE_EXECVP2': self.check_func(func='execvP', headers=['unistd.h']),
            'HAVE_EXECL': self.check_func(func='execl', headers=['unistd.h']),
            'HAVE_EXECLP': self.check_func(func='execlp', headers=['unistd.h']),
            'HAVE_EXECLE': self.check_func(func='execle', headers=['unistd.h']),
            'HAVE_POSIX_SPAWN': self.check_func(func='posix_spawn', headers=['spawn.h']),
            'HAVE_POSIX_SPAWNP': self.check_func(func='posix_spawnp', headers=['spawn.h']),
            'HAVE_NSGETENVIRON': self.check_func(func='_NSGetEnviron', headers=['crt_externs.h'])}
        config.finalize_options(self)

    def run(self):
        with open('libear/config.h', 'w+') as handle:
            from os import linesep
            handle.write('#pragma once' + linesep)
            for key, value in self.defines.items():
                if value:
                    handle.write('#define {0}'.format(key))
                else:
                    handle.write('#undef {0}'.format(key))
                handle.write(linesep)
        config.run(self)


class BuildExt(build_ext):
    def run(self):
        self.run_command('configure')
        build_ext.run(self)


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
    packages=['analyzer'],
    package_data={'analyzer': ['resources/*']},
    entry_points={
        'console_scripts': [
            'beye = analyzer.beye:main',
            'bear = analyzer.bear:main'
        ]
    },
    ext_modules=[
        Extension(
            'ear',
            language='c',
            depends=['libear/config.h'],
            sources=['libear/environ.c',
                     'libear/protocol.c',
                     'libear/stringarray.c',
                     'libear/execs.c'],
            include_dirs=[],
            define_macros=[('_GNU_SOURCE', None)],
            libraries=['dl'],
            extra_compile_args=['-std=c99', '-Wno-error=declaration-after-statement'],
            export_symbols=['vfork',
                            'execv',
                            'execve',
                            'execvp',
                            'execvP',
                            'execvpe',
                            'execl',
                            'execlp',
                            'execle',
                            'posix_spawn',
                            'posix_spawnp'])],
    cmdclass={'build_ext': BuildExt, 'configure': CreateConfig},
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
