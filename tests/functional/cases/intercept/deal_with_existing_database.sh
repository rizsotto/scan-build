#!/usr/bin/env bash
# RUN: sh %s
# this script run the whole test, not other control from lit

set -o errexit
set -o nounset
set -o xtrace

PREFIX="${test_output_dir}/output_handling"

cat > ${PREFIX}.compile_main.sh << EOF
set -o errexit
set -o nounset
set -o xtrace

cd "${test_input_dir}"
\${CC} -c -o ${test_output_dir}/main.o main.c
EOF

cat > ${PREFIX}.compile_dirty.sh << EOF
set -o errexit
set -o nounset
set -o xtrace

cd "${test_input_dir}/dirty"
\${CC} -c -o ${test_output_dir}/dirty_one.o one.c
\${CC} -c -o ${test_output_dir}/dirty_two.o two.c
EOF

cat > ${PREFIX}.main.json << EOF
[
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/main.o main.c",
  "file": "${test_input_dir}/main.c"
}
]
EOF

cat > ${PREFIX}.dirty.json << EOF
[
{
  "directory": "${test_input_dir}/dirty",
  "command": "cc -c -o ${test_output_dir}/dirty_one.o one.c",
  "file": "${test_input_dir}/dirty/one.c"
}
,
{
  "directory": "${test_input_dir}/dirty",
  "command": "cc -c -o ${test_output_dir}/dirty_two.o two.c",
  "file": "${test_input_dir}/dirty/two.c"
}
]
EOF

cat > ${PREFIX}.final.json << EOF
[
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/main.o main.c",
  "file": "${test_input_dir}/main.c"
}
,
{
  "directory": "${test_input_dir}/dirty",
  "command": "cc -c -o ${test_output_dir}/dirty_one.o one.c",
  "file": "${test_input_dir}/dirty/one.c"
}
,
{
  "directory": "${test_input_dir}/dirty",
  "command": "cc -c -o ${test_output_dir}/dirty_two.o two.c",
  "file": "${test_input_dir}/dirty/two.c"
}
]
EOF

# preparation: create a simple compilation database
intercept-build --cdb ${PREFIX}.json sh ${PREFIX}.compile_main.sh
cdb_diff ${PREFIX}.main.json ${PREFIX}.json
# overwrite the previously created compilation database
intercept-build --cdb ${PREFIX}.json sh ${PREFIX}.compile_dirty.sh
cdb_diff ${PREFIX}.dirty.json ${PREFIX}.json
# append to the previously created compilation database
intercept-build --cdb ${PREFIX}.json --append sh ${PREFIX}.compile_main.sh
cdb_diff ${PREFIX}.final.json ${PREFIX}.json
