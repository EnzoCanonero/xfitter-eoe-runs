#!/bin/bash
# Source this to set up the environment for xfitter runs.
# Used by condor job scripts and for interactive testing.

fail_setup() {
    echo "setup_env.sh: $1" >&2
    return 1 2>/dev/null || exit 1
}

# 1) Base LCG environment from CVMFS
LCG_SETUP="/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/setup.sh"
[ -r "$LCG_SETUP" ] || fail_setup "cannot read $LCG_SETUP"
source "$LCG_SETUP" || fail_setup "failed to source $LCG_SETUP"

# Source the xFitter setup from NFS location (accessible to Condor workers)
# Set XFITTER_ROOT before sourcing this file to override the default install path.
# Need to cd to the PDF directory first so the setup.sh can read the version file
XFITTER_SETUP_ROOT="${XFITTER_ROOT:-/nfs/scratch2/ecanoner/PDF}"
XFITTER_SETUP="$XFITTER_SETUP_ROOT/setup.sh"
[ -r "$XFITTER_SETUP" ] || fail_setup "cannot read $XFITTER_SETUP"

pushd "$XFITTER_SETUP_ROOT" > /dev/null || fail_setup "cannot cd to $XFITTER_SETUP_ROOT"
source "$XFITTER_SETUP" || { popd > /dev/null; fail_setup "failed to source $XFITTER_SETUP"; }
popd > /dev/null || fail_setup "failed to return from $XFITTER_SETUP_ROOT"
