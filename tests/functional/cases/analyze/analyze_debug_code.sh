#!/usr/bin/env bash

# XFAIL: *
# RUN: bash %s %T/analyze_debug_code
# RUN: cd %T/analyze_debug_code; %{scan-build} -o . --status-bugs --force-analyze-debug-code ./run.sh

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

source_file="${root_dir}/src/broken.c"
cat >> "${source_file}" << EOF
#if NDEBUG
void bad_guy(int * i) { ; }
#else
void bad_guy(int * i) { *i = 9; }
#endif
void test() {
    int * ptr = 0;
    bad_guy(ptr);
}
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
