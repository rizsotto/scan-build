#!/usr/bin/env bash

# RUN: bash %s %T/report_file_format
# RUN: cd %T/report_file_format; %{scan-build} --output . --keep-empty bash ./run.sh | bash ./check_html.sh
# RUN: cd %T/report_file_format; %{scan-build} --output . --keep-empty --plist bash ./run.sh | bash ./check_plist.sh
# RUN: cd %T/report_file_format; %{scan-build} --output . --keep-empty --plist-html bash ./run.sh | bash ./check_html.sh
# RUN: cd %T/report_file_format; %{scan-build} --output . --keep-empty --plist-html bash ./run.sh | bash ./check_plist.sh

set -o errexit
set -o nounset
set -o xtrace

# the test creates a subdirectory inside output dir.
#
# ${root_dir}
# ├── run.sh
# ├── check_plist.sh
# ├── check_html.sh
# └── src
#    └── broken.c

root_dir=$1
mkdir -p "${root_dir}/src"

cp "${test_input_dir}/div_zero.c" "${root_dir}/src/broken.c"

cat >> "${root_dir}/run.sh" << EOF
\${CC} -c -o src/broken.o src/broken.c
EOF

cat >> "${root_dir}/check_plist.sh" << EOF
set -o errexit
set -o nounset
set -o xtrace

out_dir=\$(sed -n 's/\(.*\) Report directory created: \(.*\)/\2/p')
if [ -d "\$out_dir" ]
then
    ls \$out_dir/*.plist
else
    echo "output directory should exists"
    false
fi
EOF

cat >> "${root_dir}/check_html.sh" << EOF
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
