#!/usr/bin/env bash

# RUN: mkdir %T/output_dir_clean_when_empty
# RUN: cd %T/output_dir_clean_when_empty; %{scan-build} --output . true | bash %s
# RUN: cd %T/output_dir_clean_when_empty; %{scan-build} --output . --status-bugs true | bash %s
# RUN: cd %T/output_dir_clean_when_empty; %{scan-build} --output . --status-bugs false | bash %s
# RUN: cd %T/output_dir_clean_when_empty; %{scan-build} --output . --status-bugs --plist true | bash %s
# RUN: cd %T/output_dir_clean_when_empty; %{scan-build} --output . --status-bugs --plist false | bash %s

set -o errexit
set -o nounset
set -o xtrace

out_dir=$(sed -n 's/\(.*\) Report directory created: \(.*\)/\2/p')
if [ -d "$out_dir" ]
then
    echo "output directory should not exists"
    false
fi
