#!/usr/bin/env bash

# RUN: bash %s %T/language_specified
# RUN: cd %T/language_specified; %{analyze-build} -o . --cdb input.json | ./check.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── input.json
# ├── check.sh
# └── src
#    └── empty.c

root_dir=$1
mkdir -p "${root_dir}/src"

touch "${root_dir}/src/empty.c"

cat >> "${root_dir}/input.json" << EOF
[
  {
    "directory": "${root_dir}",
    "file": "${root_dir}/src/empty.c",
    "command": "cc -c ./src/empty.c -o ./src/empty.o -Dver=1"
  },
  {
    "directory": "${root_dir}",
    "file": "${root_dir}/src/empty.c",
    "command": "cc -c ./src/empty.c -o ./src/empty.o -Dver=2 -x c"
  },
  {
    "directory": "${root_dir}",
    "file": "${root_dir}/src/empty.c",
    "command": "cc -c ./src/empty.c -o ./src/empty.o -Dver=3 -x c++"
  },
  {
    "directory": "${root_dir}",
    "file": "${root_dir}/src/empty.c",
    "command": "cc -c ./src/empty.c -o ./src/empty.o -Dver=4 -x fortran"
  }
]
EOF

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

    if [ \$(echo "\$runs" | grep -- "\$pattern" | wc -l) -eq 0 ]; then
        echo "\$message" && false;
    fi
}

assert_not_present() {
    local pattern="\$1";
    local message="\$2";

    if [ \$(echo "\$runs" | grep -- "\$pattern" | wc -l) -gt 0 ]; then
        echo "\$message" && false;
    fi
}

assert_present     "ver=1" "default language was analised"
assert_present     "ver=2" "given language (c) was analised"
assert_present     "ver=3" "given language (c++) was analised"
assert_not_present "ver=4" "not supported language was not analised"

assert_present     "ver=8" "test assert present" || true
assert_not_present "ver=1" "test assert not present" || true
EOF
chmod +x ${checker_file}
