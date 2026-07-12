#!/bin/bash
# Source this to set up the environment for xfitter runs.
# Used by condor job scripts and for interactive testing.

fail_setup() {
    echo "setup_env.sh: $1" >&2
    return 1 2>/dev/null || exit 1
}

# Load .env from repo root if it exists (sets XFITTER_ROOT, etc.)
_SETUP_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$_SETUP_ENV_DIR/.env" ] && source "$_SETUP_ENV_DIR/.env"
unset _SETUP_ENV_DIR

# 1) Base LCG environment from CVMFS
LCG_SETUP="/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/setup.sh"
[ -r "$LCG_SETUP" ] || fail_setup "cannot read $LCG_SETUP"
source "$LCG_SETUP" || fail_setup "failed to source $LCG_SETUP"

# Source the xFitter setup from NFS location (accessible to Condor workers)
# Set XFITTER_ROOT in .env or environment before sourcing this script.
# Need to cd to the PDF directory first so the setup.sh can read the version file
XFITTER_SETUP_ROOT="${XFITTER_ROOT:?Set XFITTER_ROOT in .env at the repo root}"
XFITTER_SETUP="$XFITTER_SETUP_ROOT/setup.sh"
[ -r "$XFITTER_SETUP" ] || fail_setup "cannot read $XFITTER_SETUP"

pushd "$XFITTER_SETUP_ROOT" > /dev/null || fail_setup "cannot cd to $XFITTER_SETUP_ROOT"
source "$XFITTER_SETUP" || { popd > /dev/null; fail_setup "failed to source $XFITTER_SETUP"; }
popd > /dev/null || fail_setup "failed to return from $XFITTER_SETUP_ROOT"

# 3) Optional: select a specific xFitter build tree (git worktree) instead of
# the default one baked into $XFITTER_ROOT/setup.sh (xfitter-master, i.e. the
# errors-on-errors branch). Set XFITTER_TREE in .env or the environment to:
#   - a directory name under $XFITTER_ROOT, e.g. XFITTER_TREE=xfitter-bartlett-fixes
#   - an absolute path to a built tree
# Leave it unset/empty to keep the default. Each tree's xfitter binary carries
# an absolute RPATH to its own lib/xfitter modules, so prepending its bin/ (and
# lib/) is enough to run that build; deps are shared across trees.
if [ -n "${XFITTER_TREE:-}" ]; then
    case "$XFITTER_TREE" in
        /*) _xf_tree="$XFITTER_TREE" ;;
        *)  _xf_tree="$XFITTER_SETUP_ROOT/$XFITTER_TREE" ;;
    esac
    # Hard stop rather than silent fallback to the default tree: if the tree was
    # requested explicitly it must be built, else the run would use the wrong
    # binary. fail_setup's return is swallowed inside its function when sourced,
    # so abort here at top level.
    if [ ! -x "$_xf_tree/bin/xfitter" ]; then
        echo "setup_env.sh: XFITTER_TREE=$XFITTER_TREE: no built xfitter at $_xf_tree/bin/xfitter" >&2
        unset _xf_tree
        return 1 2>/dev/null || exit 1
    fi
    export PATH="$_xf_tree/bin:$PATH"
    export LD_LIBRARY_PATH="$_xf_tree/lib:$_xf_tree/lib/xfitter:${LD_LIBRARY_PATH}"
    echo "setup_env.sh: using xFitter tree $_xf_tree ($(command -v xfitter))" >&2
    unset _xf_tree
fi
