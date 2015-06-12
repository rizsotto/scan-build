#!/usr/bin/env bash

set -o nounset
set -o errexit

SCRIPT_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

"$SCRIPT_DIR/scan-build" all $@
