#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/logs" "$DIR/../output"
condor_submit "$DIR/job.sub"
