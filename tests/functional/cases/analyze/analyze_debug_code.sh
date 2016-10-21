#!/usr/bin/env bash

# XFAIL: *
# RUN: bash %s %T/debug_code
# RUN: cd %T/debug_code; %{scan-build} -o . --status-bugs --force-analyze-debug-code ./run.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── run.sh
# └── src
#    └── broken.c

root_dir=$1
mkdir -p "${root_dir}/src"

cat >> "${root_dir}/src/broken.c" << EOF
#if NDEBUG
#else
EOF
cat >> "${root_dir}/src/broken.c" < "${test_input_dir}/div_zero.c"
cat >> "${root_dir}/src/broken.c" << EOF
#endif
EOF

build_file="${root_dir}/run.sh"
cat >> ${build_file} << EOF
#!/usr/bin/env bash

set -o nounset
set -o xtrace

"\$CC" -c ./src/broken.c -o ./src/broken.o -DNDEBUG;
true;
EOF
chmod +x ${build_file}
