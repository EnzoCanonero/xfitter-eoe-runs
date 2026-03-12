#!/bin/bash
# xFitter fit execution script
set -e

CONFIGDIR="/nfs/scratch2/ecanoner/xfitter-eoe-runs/fits/hera/hera-baseline/nominal/config"
source "/nfs/scratch2/ecanoner/xfitter-eoe-runs/setup_env.sh"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=$(mktemp -d)
trap "rm -rf $SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \
      "$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="$SHIM_DIR:$LD_LIBRARY_PATH"

cd "$CONFIGDIR"
xfitter
