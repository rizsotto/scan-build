#!/usr/bin/env bash

# RUN: bash %s %T
# RUN: cd %T; %{scan-wrapped-build} -o . --intercept-first ./run.sh | ./check.sh
# RUN: cd %T; %{scan-wrapped-build} -o . --intercept-first --override-compiler ./run.sh | ./check.sh
# RUN: cd %T; %{scan-wrapped-build} -o . --override-compiler ./run.sh | ./check.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── wrapper
# ├── wrapper++
# ├── run.sh
# ├── check.sh
# └── src
#    └── broken.c

root_dir=$1
mkdir -p "${root_dir}/src"

cp "${test_input_dir}/div_zero.c" "${root_dir}/src/broken.c"

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

"\$CC" -c -o ./src/empty.o ./src/broken.c;
"\$CXX" -c -o ./src/empty.o ./src/broken.c;

cd src
"\$CC" -c -o ./empty.o ./broken.c;
"\$CXX" -c -o ./empty.o ./broken.c;
EOF
chmod +x ${build_file}

check_two="${root_dir}/check.sh"
cat >> "${check_two}" << EOF
#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o xtrace

out_dir=\$(sed -n 's/\(.*\) Report directory created: \(.*\)/\2/p')
if [ -d "\$out_dir" ]
then
    ls "\$out_dir/index.html"
    ls \$out_dir/report-*.html
else
    echo "output directory should exists"
    false
fi
EOF
chmod +x "${check_two}"
