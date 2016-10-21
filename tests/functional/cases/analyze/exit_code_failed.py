# XFAIL: *
# RUN: mkdir %T/exit_code_for_fail
# RUN: cd %T/exit_code_for_fail; %{scan-build} false
