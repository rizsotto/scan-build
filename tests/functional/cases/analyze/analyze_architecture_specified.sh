#!/usr/bin/env bash

# RUN: bash %s %T/analyze_architecture_specified
# RUN: cd %T/analyze_architecture_specified; %{scan-build} -o . --intercept-first ./run.sh | ./check.sh
# RUN: cd %T/analyze_architecture_specified; %{scan-build} -o . --intercept-first  --override-compiler ./run.sh | ./check.sh
# RUN: cd %T/analyze_architecture_specified; %{scan-build} -o . --override-compiler ./run.sh | ./check.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── run.sh
# ├── check.sh
# └── src
#    └── empty.c

root_dir=$1
mkdir -p "${root_dir}/src"

touch "${root_dir}/src/empty.c"

build_file="${root_dir}/run.sh"
cat >> ${build_file} << EOF
#!/usr/bin/env bash

set -o nounset
set -o xtrace

"\$CC" -c ./src/empty.c -o ./src/empty.o -Dver=1;
"\$CC" -c ./src/empty.c -o ./src/empty.o -Dver=2 -arch i386;
"\$CC" -c ./src/empty.c -o ./src/empty.o -Dver=3 -arch x86_64;
"\$CC" -c ./src/empty.c -o ./src/empty.o -Dver=4 -arch ppc;
true;
EOF
chmod +x ${build_file}

checker_file="${root_dir}/check.sh"
cat >> ${checker_file} << EOF
#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o xtrace

runs=\$(grep "exec command" | sort | uniq)

assert_present() {
    local pattern="\$1";
    local message="\$2";

    if [ \$(echo "\$runs" | grep "\$pattern" | wc -l) -eq 0 ]; then
        echo "\$message" && false;
    fi
}

assert_not_present() {
    local pattern="\$1";
    local message="\$2";

    if [ \$(echo "\$runs" | grep "\$pattern" | wc -l) -gt 0 ]; then
        echo "\$message" && false;
    fi
}

assert_present     "ver=1" "default architecture was not executed"
assert_present     "ver=2" "given architecture (i386) was not executed"
assert_present     "ver=3" "given architecture (x86_64) was not executed"
assert_not_present "ver=4" "not supported architecture was executed"

assert_present     "ver=8" "test assert present" || true
assert_not_present "ver=1" "test assert not present" || true
EOF
chmod +x ${checker_file}
