#!/usr/bin/env bash
# RUN: intercept-build --cdb %t.json.result sh %s
# RUN: cdb_diff %T/flags_are_filtered.sh.json %t.json.result

set -o errexit
set -o nounset
set -o xtrace

# set up unique names for this test
PREFIX=flagfiltering
# set up platform specific linker options
if [ `uname -o | grep -i linux` ]; then
  LD_FLAGS="-o ${test_output_dir}/lib${PREFIX}.so -shared -Wl,-soname,${PREFIX}"
elif [ `uname -o | grep -i darwin` ]; then
  LD_FLAGS="-o ${test_output_dir}/lib${PREFIX}.dylib -dynamiclib -install_name @rpath/${PREFIX}"
fi

cd ${test_input_dir}

# non compilation calls shall not be in the result
${CC} -### -c main.c 2> /dev/null
${CC} -E -o "${test_output_dir}/$$.i" main.c
${CC} -S -o "${test_output_dir}/$$.asm" main.c
${CC} -c -o "${test_output_dir}/$$.d" -M main.c
${CC} -c -o "${test_output_dir}/$$.d" -MM main.c

# preprocessor flags shall be filtered
${CC} -c -o "${test_output_dir}/${PREFIX}_clean_one.o" -fpic -Iclean/include -MD -MT target -MF "${test_output_dir}/${PREFIX}_clean_one.d" clean/one.c
${CC} -c -o "${test_output_dir}/${PREFIX}_clean_two.o" -fpic -Iclean/include -MMD -MQ target -MF "${test_output_dir}/${PREFIX}_clean_two.d" clean/two.c

# linking shall not in the result
${CC} ${LD_FLAGS} "${test_output_dir}/${PREFIX}_clean_one.o" "${test_output_dir}/${PREFIX}_clean_two.o"

# linker flags shall be filtered
${CC} -o "${test_output_dir}/${PREFIX}_one" "-l${PREFIX}" "-L${test_output_dir}" main.c
${CC} -o "${test_output_dir}/${PREFIX}_two" -l ${PREFIX} -L ${test_output_dir} main.c

cat > ${test_output_dir}/flags_are_filtered.sh.json << EOF
[
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/${PREFIX}_clean_one.o -fpic -Iclean/include clean/one.c",
  "file": "${test_input_dir}/clean/one.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/${PREFIX}_clean_two.o -fpic -Iclean/include clean/two.c",
  "file": "${test_input_dir}/clean/two.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/${PREFIX}_one main.c",
  "file": "${test_input_dir}/main.c"
}
,
{
  "directory": "${test_input_dir}",
  "command": "cc -c -o ${test_output_dir}/${PREFIX}_two main.c",
  "file": "${test_input_dir}/main.c"
}
]
EOF
