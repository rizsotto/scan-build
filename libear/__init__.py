# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.
"""
. """

import sys
import os
import os.path
import re
import logging

__all__ = ['ear_library']


def ear_library(compiler, dst_dir):
    """ Returns the full path to the 'libear' library. """

    try:
        src_dir = os.path.dirname(os.path.realpath(__file__))
        with make_context(src_dir) as context:
            context.set_compiler(compiler)
            context.set_language_standard('c99')
            context.add_definitions(['-D_GNU_SOURCE'])

            with Configure(context) as configure:
                configure.check_function_exists('execve', 'HAVE_EXECVE')
                configure.check_function_exists('execv', 'HAVE_EXECV')
                configure.check_function_exists('execvpe', 'HAVE_EXECVPE')
                configure.check_function_exists('execvp', 'HAVE_EXECVP')
                configure.check_function_exists('execvP', 'HAVE_EXECVP2')
                configure.check_function_exists('execl', 'HAVE_EXECL')
                configure.check_function_exists('execlp', 'HAVE_EXECLP')
                configure.check_function_exists('execle', 'HAVE_EXECLE')
                configure.check_function_exists('posix_spawn',
                                                'HAVE_POSIX_SPAWN')
                configure.check_function_exists('posix_spawnp',
                                                'HAVE_POSIX_SPAWNP')
                configure.check_symbol_exists('_NSGetEnviron', 'crt_externs.h',
                                              'HAVE_NSGETENVIRON')
                configure.write_by_template(
                    os.path.join(src_dir, 'config.h.in'),
                    os.path.join(dst_dir, 'config.h'))
            with SharedLibrary('ear', context) as target:
                target.add_include(dst_dir)
                target.add_sources('ear.c')
                target.link_against(context.dl_libraries())
                target.build_release(dst_dir)
                return os.path.join(dst_dir, target.name)

    except Exception:
        logging.info("Could not build interception library.", exc_info=True)
        return None


def execute(cmd, *args, **kwargs):
    """ Make subprocess execution silent. """

    import subprocess
    kwargs.update({'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT})
    return subprocess.check_call(cmd, *args, **kwargs)


class TemporaryDirectory(object):
    """ This function creates a temporary directory using mkdtemp() (the
    supplied arguments are passed directly to the underlying function).
    The resulting object can be used as a context manager. On completion
    of the context or destruction of the temporary directory object the
    newly created temporary directory and all its contents are removed
    from the filesystem. """

    def __init__(self, **kwargs):
        from tempfile import mkdtemp
        self.name = mkdtemp(**kwargs)

    def __enter__(self):
        return self.name

    def __exit__(self, _type, _value, _traceback):
        self.cleanup()

    def cleanup(self):
        from shutil import rmtree
        if self.name is not None:
            rmtree(self.name)


class Context:
    """ Abstract class to represent different toolset. """

    def __init__(self, src_dir):
        self.src_dir = src_dir
        self.compiler = None
        self.c_flags = []

    def __enter__(self):
        """ declared to work 'with'. """
        return self

    def __exit__(self, _type, _value, _traceback):
        """ declared to work 'with'. """
        pass

    def set_compiler(self, compiler):
        """ part of public interface """
        self.compiler = compiler

    def set_language_standard(self, standard):
        """ part of public interface """
        self.c_flags.append('-std=' + standard)

    def add_definitions(self, defines):
        """ part of public interface """
        self.c_flags.extend(defines)

    def dl_libraries(self):
        pass

    def shared_library_name(self, name):
        pass

    def shared_library_c_flags(self, release):
        extra = ['-DNDEBUG', '-O3'] if release else []
        return extra + ['-fPIC'] + self.c_flags

    def shared_library_ld_flags(self, release, name):
        pass


class DarwinContext(Context):
    def __init__(self, src_dir):
        Context.__init__(self, src_dir)

    def dl_libraries(self):
        return []

    def shared_library_name(self, name):
        return 'lib' + name + '.dylib'

    def shared_library_ld_flags(self, release, name):
        extra = ['-dead_strip'] if release else []
        return extra + ['-dynamiclib', '-install_name', '@rpath/' + name]


class UnixContext(Context):
    def __init__(self, src_dir):
        Context.__init__(self, src_dir)

    def dl_libraries(self):
        return []

    def shared_library_name(self, name):
        return 'lib' + name + '.so'

    def shared_library_ld_flags(self, release, name):
        extra = [] if release else []
        return extra + ['-shared', '-Wl,-soname,' + name]


class LinuxContext(UnixContext):
    def __init__(self, src_dir):
        UnixContext.__init__(self, src_dir)

    def dl_libraries(self):
        return ['dl']


def make_context(src_dir):
    platform = sys.platform
    if platform in {'win32', 'cygwin'}:
        raise RuntimeError('not implemented on this platform')
    elif platform == 'darwin':
        return DarwinContext(src_dir)
    elif platform in {'linux', 'linux2'}:
        return LinuxContext(src_dir)
    else:
        return UnixContext(src_dir)


class Configure:
    def __init__(self, context):
        self.ctx = context
        self.results = {'APPLE': sys.platform == 'darwin'}

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        pass

    def _try_to_compile_and_link(self, source):
        try:
            with TemporaryDirectory() as work_dir:
                src_file = 'check.c'
                with open(os.path.join(work_dir, src_file), 'w') as handle:
                    handle.write(source)

                execute([self.ctx.compiler, src_file], cwd=work_dir)
                return True
        except Exception:
            return False

    def check_function_exists(self, function, name):
        template = "int FUNCTION(); int main() { return FUNCTION(); }"
        source = template.replace("FUNCTION", function)

        logging.debug('Checking function %s', function)
        found = self._try_to_compile_and_link(source)
        logging.debug('Checking function %s -- %s', function,
                      'found' if found else 'not found')
        self.results.update({name: found})

    def check_symbol_exists(self, symbol, include, name):
        template = """#include <INCLUDE>
                      int main() { return ((int*)(&SYMBOL))[0]; }"""
        source = template.replace('INCLUDE', include).replace("SYMBOL", symbol)

        logging.debug('Checking symbol %s', symbol)
        found = self._try_to_compile_and_link(source)
        logging.debug('Checking symbol %s -- %s', symbol,
                      'found' if found else 'not found')
        self.results.update({name: found})

    def write_by_template(self, template, output):
        def transform(line, definitions):

            pattern = re.compile(r'^#cmakedefine\s+(\S+)')
            m = pattern.match(line)
            if m:
                key = m.group(1)
                if key not in definitions or not definitions[key]:
                    return '/* #undef {} */\n'.format(key)
                else:
                    return '#define {}\n'.format(key)
            return line

        with open(template, 'r') as src_handle:
            logging.debug('Writing config to %s', output)
            with open(output, 'w') as dst_handle:
                for line in src_handle:
                    dst_handle.write(transform(line, self.results))


class SharedLibrary:
    def __init__(self, name, context):
        self.name = context.shared_library_name(name)
        self.ctx = context
        self.inc = []
        self.src = []
        self.lib = []

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        pass

    def add_include(self, directory):
        self.inc.extend(['-I', directory])

    def add_sources(self, source):
        self.src.append(source)

    def link_against(self, libraries):
        self.lib.extend(['-l' + lib for lib in libraries])

    def build_release(self, directory):
        for src in self.src:
            logging.debug('Compiling %s', src)
            execute(
                [self.ctx.compiler, '-c', os.path.join(self.ctx.src_dir, src),
                 '-o', src + '.o'] + self.inc +
                self.ctx.shared_library_c_flags(True),
                cwd=directory)
        logging.debug('Linking %s', self.name)
        execute(
            [self.ctx.compiler] + [src + '.o' for src in self.src] +
            ['-o', self.name] + self.lib +
            self.ctx.shared_library_ld_flags(True, self.name),
            cwd=directory)
