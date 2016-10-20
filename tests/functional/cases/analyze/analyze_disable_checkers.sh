#!/usr/bin/env bash

# RUN: bash %s %T/disable_checkers
# RUN: cd %T/disable_checkers; %{analyze-build} -o . --status-bugs --disable-checker core.NullDereference --cdb input.json

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── input.json
# ├── check.sh
# └── src
#    └── broken.c

root_dir=$1
mkdir -p "${root_dir}/src"

cat >> "${root_dir}/src/broken.c" << EOF
int bad_guy(int * i)
{
    *i = 9;
    return *i;
}

void bad_guy_test()
{
    int * ptr = 0;
    bad_guy(ptr);
}
EOF

cat >> "${root_dir}/input.json" << EOF
[
    {
        "directory": "${root_dir}",
        "file": "${root_dir}/src/broken.c",
        "command": "cc -c ./src/broken.c -o ./src/broken.o"
    }
]
EOF
