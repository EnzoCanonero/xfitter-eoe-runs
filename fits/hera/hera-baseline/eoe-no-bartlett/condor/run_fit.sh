#!/bin/bash
FITDIR="/nfs/scratch2/ecanoner/xfitter-eoe-runs/fits/hera/hera-baseline/eoe-no-bartlett"
source "/nfs/scratch2/ecanoner/xfitter-eoe-runs/setup_env.sh"
cd "$FITDIR"

# Stage config files into CWD for xfitter
for f in config/*; do
    ln -sf "$f" .
done

xfitter
rc=$?

# Clean up staged symlinks
for f in config/*; do
    rm -f "$(basename "$f")"
done

exit $rc
