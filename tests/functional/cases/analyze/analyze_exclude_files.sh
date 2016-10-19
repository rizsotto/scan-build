#!/usr/bin/env bash

# RUN: bash %s %T/analyze_exclude_files
# RUN: cd %T/analyze_exclude_files; %{scan-build} -o . --exclude src/ignore --intercept-first ./run.sh | ./check.sh
# RUN: cd %T/analyze_exclude_files; %{scan-build} -o . --exclude src/ignore --intercept-first  --override-compiler ./run.sh | ./check.sh
# RUN: cd %T/analyze_exclude_files; %{scan-build} -o . --exclude src/ignore --override-compiler ./run.sh | ./check.sh
# RUN: cd %T/analyze_exclude_files; %{scan-build} -o . --exclude %T/analyze_exclude_files/src/ignore --intercept-first ./run.sh | ./check.sh
# RUN: cd %T/analyze_exclude_files; %{scan-build} -o . --exclude %T/analyze_exclude_files/src/ignore --intercept-first  --override-compiler ./run.sh | ./check.sh
# RUN: cd %T/analyze_exclude_files; %{scan-build} -o . --exclude %T/analyze_exclude_files/src/ignore --override-compiler ./run.sh | ./check.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}

root_dir=$1
mkdir -p "${root_dir}/src/ignore"

touch "${root_dir}/src/empty.c"
touch "${root_dir}/src/ignore/empty.c"

build_file="${root_dir}/run.sh"
cat >> ${build_file} << EOF
#!/usr/bin/env bash

set -o nounset
set -o xtrace

"\$CC" -c ./src/empty.c -o ./src/empty.o -Dver=1;
"\$CC" -c "${root_dir}/src/empty.c" -o ./src/empty.o -Dver=2;
"\$CC" -c ./src/ignore/empty.c -o ./src/ignore/empty.o -Dver=3;
"\$CC" -c "${root_dir}/src/ignore/empty.c" -o ./src/ignore/empty.o -Dver=4;
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

assert_present     "ver=1" "analyzer shall run against ver=1"
assert_present     "ver=2" "analyzer shall run against ver=2"
assert_not_present "ver=3" "analyzer shall not run against ver=3"
assert_not_present "ver=4" "analyzer shall not run against ver=4"

assert_present     "ver=8" "test assert present" || true
assert_not_present "ver=1" "test assert not present" || true
EOF
chmod +x ${checker_file}
