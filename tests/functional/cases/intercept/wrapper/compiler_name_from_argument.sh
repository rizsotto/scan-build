#!/usr/bin/env bash

# RUN: bash %s %T
# RUN: cd %T; %{intercept-wrapped-build} --cdb wrapper.json --override-compiler ./run.sh
# RUN: cd %T; cdb_diff wrapper.json expected.json
#
# when library preload disabled, it falls back to use compiler wrapper
#
# RUN: cd %T; %{intercept-wrapped-build} --cdb preload.json ./run.sh
# RUN: cd %T; cdb_diff preload.json expected.json

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── wrapper
# ├── wrapper++
# ├── run.sh
# ├── expected.json
# └── src
#    └── empty.c

root_dir=$1
mkdir -p "${root_dir}/src"

touch "${root_dir}/src/empty.c"

wrapper_file="${root_dir}/wrapper"
cat >> ${wrapper_file} << EOF
#!/usr/bin/env bash

set -o xtrace

${REAL_CC} \$@
EOF
chmod +x ${wrapper_file}

wrapperxx_file="${root_dir}/wrapper++"
cat >> ${wrapperxx_file} << EOF
#!/usr/bin/env bash

set -o xtrace

${REAL_CXX} \$@
EOF
chmod +x ${wrapperxx_file}

build_file="${root_dir}/run.sh"
cat >> ${build_file} << EOF
#!/usr/bin/env bash

set -o nounset
set -o xtrace

"\$CC" -c -o ./src/empty.o -Dver=1 ./src/empty.c;
"\$CXX" -c -o ./src/empty.o -Dver=2 ./src/empty.c;

cd src
"\$CC" -c -o ./empty.o -Dver=3 ./empty.c;
"\$CXX" -c -o ./empty.o -Dver=4 ./empty.c;
EOF
chmod +x ${build_file}

cat >> "${root_dir}/expected.json" << EOF
[
{
  "command": "cc -c -o ./src/empty.o -Dver=1 ./src/empty.c",
  "directory": "${root_dir}",
  "file": "${root_dir}/src/empty.c"
}
,
{
  "command": "c++ -c -o ./src/empty.o -Dver=2 ./src/empty.c",
  "directory": "${root_dir}",
  "file": "${root_dir}/src/empty.c"
}
,
{
  "command": "cc -c -o ./empty.o -Dver=3 ./empty.c",
  "directory": "${root_dir}/src",
  "file": "${root_dir}/src/empty.c"
}
,
{
  "command": "c++ -c -o ./empty.o -Dver=4 ./empty.c",
  "directory": "${root_dir}/src",
  "file": "${root_dir}/src/empty.c"
}
]
EOF
