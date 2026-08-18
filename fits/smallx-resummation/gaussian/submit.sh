#!/bin/bash
set -euo pipefail

if [ "${1:-}" != "--submit" ]; then
    echo "Submission is guarded. Re-run as: $0 --submit" >&2
    exit 2
fi

DIR=$(cd "$(dirname "$0")" && pwd)
FIT_DIRS="$DIR/batch/fit_dirs.txt"

while IFS= read -r fit_dir; do
    mkdir -p "$fit_dir/condor/logs" "$fit_dir/output"
    sed -i "s|^OutputDirectory:.*|OutputDirectory: \"$fit_dir/output\"|" \
        "$fit_dir/config/parameters.yaml"
done < "$FIT_DIRS"

condor_submit "$DIR/batch/condor_batch.sub"
