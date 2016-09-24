#!/usr/bin/env python
# -*- coding: utf-8 -*-
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import argparse
import json


def diff(lhs, rhs):
    def create_hash(entry):
        return entry['file'][::-1] + entry['command'] + entry['directory']

    left = {create_hash(entry): entry for entry in lhs}
    right = {create_hash(entry): entry for entry in rhs}
    result = []
    for key in left.keys():
        if key not in right:
            result.append('> {}'.format(left[key]))
    for key in right.keys():
        if key not in left:
            result.append('< {}'.format(right[key]))
    return result


def main():
    """ Semantically diff two compilation databases. """
    parser = argparse.ArgumentParser()
    parser.add_argument('left', type=argparse.FileType('r'))
    parser.add_argument('right', type=argparse.FileType('r'))
    args = parser.parse_args()
    # files are open, parse the json content
    lhs = json.load(args.left)
    rhs = json.load(args.right)
    # run the diff and print the result
    results = diff(lhs, rhs)
    for result in results:
        print(result)
    return len(results)
