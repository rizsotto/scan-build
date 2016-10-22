#!/usr/bin/env bash

# RUN: bash %s %T/output_dir_kept
# RUN: cd %T/output_dir_kept; %{scan-build} --output . bash ./run.sh | bash ./check.sh
# RUN: cd %T/output_dir_kept; %{scan-build} --output . --plist bash ./run.sh | bash ./check.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── run.sh
# ├── check.sh
# └── src
#    └── broken.c

root_dir=$1
mkdir -p "${root_dir}/src"

cp "${test_input_dir}/div_zero.c" "${root_dir}/src/broken.c"

cat >> "${root_dir}/run.sh" << EOF
\${CC} -c -o src/broken.o src/broken.c
EOF

cat >> "${root_dir}/check.sh" << EOF
set -o errexit
set -o nounset
set -o xtrace

out_dir=\$(sed -n 's/\(.*\) Report directory created: \(.*\)/\2/p')
if [ ! -d "\$out_dir" ]
then
    echo "output directory should exists"
    false
fi
EOF
