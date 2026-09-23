#!/bin/bash
set -euo pipefail
if [ -f "$2" ]; then
    cmp -s -- "$1" "$2"
else
    cp -- "$1" "$2"
fi
