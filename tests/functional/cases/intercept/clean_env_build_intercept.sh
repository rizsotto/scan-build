#!/usr/bin/env bash
# REQUIRES: preload
# RUN: intercept-build --cdb %t.json.result sh %s
# RUN: cdb_diff %T/clean_env_build_intercept.sh.json %t.json.result

set -o errexit
set -o nounset
set -o xtrace

CC=$(which clang)

cd ${test_input_dir}
env - ${CC} -c -o ${test_output_dir}/clean_env_main.o main.c

cat > ${test_output_dir}/clean_env_build_intercept.sh.json << EOF
[
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/clean_env_main.o main.c",
  "file": "${test_input_dir}/main.c"
}
]
EOF
