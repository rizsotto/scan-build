#!/usr/bin/env bash
# RUN: intercept-build --cdb %t.json.result sh %s
# RUN: cdb_diff %T/multiple_source_single_command.sh.json %t.json.result

set -o errexit
set -o nounset
set -o xtrace

cd ${test_input_dir}
${CC} -o ${test_output_dir}/all_in_one main.c dirty/one.c dirty/two.c

cat > ${test_output_dir}/multiple_source_single_command.sh.json << EOF
[
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/all_in_one main.c",
  "file": "${test_input_dir}/main.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/all_in_one dirty/one.c",
  "file": "${test_input_dir}/dirty/one.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/all_in_one dirty/two.c",
  "file": "${test_input_dir}/dirty/two.c"
}
]
EOF
