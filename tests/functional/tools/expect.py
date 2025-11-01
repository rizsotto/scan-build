#!/usr/bin/env python
#                     The LLVM Compiler Infrastructure
#
# This file is distributed under the University of Illinois Open Source
# License. See LICENSE.TXT for details.

import argparse
import json
import os
import os.path


def main():
    """append entry to a compilation database."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--cdb", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    # read existing content from target file
    entries = []
    if os.path.exists(args.cdb):
        with open(args.cdb) as handle:
            entries = json.load(handle)
    # update with the current invocation
    current = {"directory": os.getcwd(), "command": args.command, "file": args.file}
    entries.append(current)
    # write the result back
    with open(args.cdb, "w") as handle:
        json.dump(list(entries), handle, sort_keys=True, indent=4)
    return 0
