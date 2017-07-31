# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import os.path
import glob
import itertools


def _parse_symbol_map(path):
    """ Returns an iterator of the parsed entries.

    The file format is very simple: Each line is a separate entry.
    An entry is a space separated <mangled symbol name> <file name>

    :param path:    Path to the file to parse
    :return:        A generator of parsed entries. """

    with open(path, 'r') as handle:
        for line in handle:
            (symbol, module) = line.strip().split(' ', 1)
            yield (symbol, module)


def _write_symbol_map(path, iterator):
    """ Writes the symbol map entries to file

    :param path: The output file path.
    :param iterator: Iterator of (symbol, module) tuples. """

    with open(path, 'w') as handle:
        for symbol, module in iterator:
            handle.write("{} {}\n".format(symbol, module))

    return path


def _filter_symbol_map(entries):
    """ Filters out symbols which appear in multiple modules.

    :param entries: Iterator to (symbol, module) tuples.
    :return: A generator of (symbol, module) tuples. """

    result = dict()
    for symbol, module in entries:
        # get current values or a default empty set
        current = result.get(symbol, set())
        current.add(module)
        # update state
        result.update({symbol: current})
    # Do not emit those elements which appeared in multiple modules.
    return ((k, v.pop()) for k, v in result.items() if len(v) == 1)


def merge_symbol_map_files(input_dir, output_file):
    """ Read multiple symbol files and merge it into one.

    :param input_dir: directory which contains the files CTU symbol files.
    :param output_file: path to the output file which needs to be created.
    :return: path to the output file. """

    files = glob.iglob(os.path.join(input_dir, '*'))
    entries = (_parse_symbol_map(file) for file in files)
    symbol_map = _filter_symbol_map(itertools.chain.from_iterable(entries))
    return _write_symbol_map(output_file, symbol_map)
