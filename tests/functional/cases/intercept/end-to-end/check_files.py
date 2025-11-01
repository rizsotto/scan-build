#!/usr/bin/env python
# SPDX-License-Identifier: MIT

import argparse
import json
import os.path
import sys

EXPECTED = frozenset(["far.cxx", "bar.cc", "foo.cpp", "boo.c++"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=argparse.FileType("r"))
    args = parser.parse_args()
    # file is open, parse the json content
    entries = json.load(args.input)
    # just get file names
    result = {os.path.basename(entry["file"]) for entry in entries}
    return 0 if result == EXPECTED else 1


if __name__ == "__main__":
    sys.exit(main())
