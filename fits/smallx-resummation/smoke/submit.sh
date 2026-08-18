#!/bin/bash
set -euo pipefail

if [ "${1:-}" != "--submit" ]; then
    echo "Smoke-job submission is guarded. Re-run as: $0 --submit" >&2
    exit 2
fi

DIR=$(cd "$(dirname "$0")" && pwd)
FIT_DIR="$DIR/parambg-nllx"
RUNNER=$(cd "$DIR/../gaussian/batch" && pwd)/run_fit.sh
JOB_SUB="$FIT_DIR/condor/job.sub"
mkdir -p "$FIT_DIR/condor/logs" "$FIT_DIR/output"
sed -i "s|^OutputDirectory:.*|OutputDirectory: \"$FIT_DIR/output\"|" \
    "$FIT_DIR/config/parameters.yaml"

cat > "$JOB_SUB" <<EOF
universe              = vanilla
executable            = $RUNNER
arguments             = $FIT_DIR
output                = $FIT_DIR/condor/logs/output.log
error                 = $FIT_DIR/condor/logs/error.log
log                   = $FIT_DIR/condor/logs/run.log
should_transfer_files = NO
initialdir            = $FIT_DIR/config
request_cpus          = 1
request_memory        = 4GB
queue 1
EOF

condor_submit "$JOB_SUB"
