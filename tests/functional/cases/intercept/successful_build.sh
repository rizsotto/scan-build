#!/usr/bin/env bash
# RUN: intercept-build -vvv --override-compiler --cdb %t.json.wrapper sh %s
# RUN: cdb_diff %t.json.wrapper %T/successful_build.json.expected
#
# when library preload disabled, it falls back to use compiler wrapper
#
# RUN: intercept-build -vvv --cdb %t.json.preload sh %s
# RUN: cdb_diff %t.json.preload %T/successful_build.json.expected

set -o errexit
set -o nounset
set -o xtrace

cd "${test_input_dir}"
${CC}  -c -o ${test_output_dir}/main.o main.c
cd "${test_input_dir}/clean"
${CC}  -c -o ${test_output_dir}/clean_one.o -Iinclude one.c
cd "${test_input_dir}"
${CXX} -c -o ${test_output_dir}/clean_two.o -I ./clean/include clean/two.c
cd "${test_input_dir}/dirty"
${CC}  -c -o ${test_output_dir}/dirty_one.o -Wall one.c
cd "${test_input_dir}"
${CXX} -c -o ${test_output_dir}/dirty_two.o -Wall dirty/two.c

cat > ${test_output_dir}/successful_build.json.expected << EOF
[
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/main.o main.c",
  "file": "${test_input_dir}/main.c"
}
,
{
  "directory": "${test_input_dir}/clean",
  "command": "cc -c -o ${test_output_dir}/clean_one.o -Iinclude one.c",
  "file": "${test_input_dir}/clean/one.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "c++ -c -o ${test_output_dir}/clean_two.o -I ./clean/include clean/two.c",
  "file": "${test_input_dir}/clean/two.c"
}
,
{
  "directory": "${test_input_dir}/dirty",
  "command": "cc -c -o ${test_output_dir}/dirty_one.o -Wall one.c",
  "file": "${test_input_dir}/dirty/one.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "c++ -c -o ${test_output_dir}/dirty_two.o -Wall dirty/two.c",
  "file": "${test_input_dir}/dirty/two.c"
}
]
EOF
