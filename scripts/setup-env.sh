#!/bin/bash
# Source this to set up the environment for xfitter runs.
# Used by condor job scripts and for interactive testing.

fail_setup() {
    echo "setup-env.sh: $1" >&2
    return 1
}

# Load .env from repo root if it exists (sets XFITTER_ROOT, etc.). Explicit
# caller-provided tree/commit values are authoritative: study-generated job
# scripts use them to pin a build and must not be silently overridden by a
# local .env.
_XFITTER_TREE_WAS_SET=0
if [ "${XFITTER_TREE+x}" = x ]; then
    _XFITTER_TREE_WAS_SET=1
    _XFITTER_TREE_CALLER_VALUE="$XFITTER_TREE"
fi
_XFITTER_COMMIT_WAS_SET=0
if [ "${XFITTER_COMMIT+x}" = x ]; then
    _XFITTER_COMMIT_WAS_SET=1
    _XFITTER_COMMIT_CALLER_VALUE="$XFITTER_COMMIT"
fi
_SETUP_ENV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$_SETUP_ENV_ROOT/.env" ] && source "$_SETUP_ENV_ROOT/.env"
unset _SETUP_ENV_ROOT
if [ "$_XFITTER_TREE_WAS_SET" -eq 1 ]; then
    export XFITTER_TREE="$_XFITTER_TREE_CALLER_VALUE"
    # A commit from .env belongs to its default tree. Do not accidentally apply
    # it when a generated worker/caller explicitly selects another tree without
    # also supplying that tree's own pin.
    if [ "$_XFITTER_COMMIT_WAS_SET" -eq 0 ]; then
        unset XFITTER_COMMIT
    fi
fi
if [ "$_XFITTER_COMMIT_WAS_SET" -eq 1 ]; then
    export XFITTER_COMMIT="$_XFITTER_COMMIT_CALLER_VALUE"
fi
unset _XFITTER_TREE_WAS_SET _XFITTER_TREE_CALLER_VALUE
unset _XFITTER_COMMIT_WAS_SET _XFITTER_COMMIT_CALLER_VALUE

# Values loaded from .env must also be visible to child processes such as the
# Python plotting commands. Caller-provided values were already exported above.
export XFITTER_ROOT
[ -z "${XFITTER_TREE+x}" ] || export XFITTER_TREE
[ -z "${XFITTER_COMMIT+x}" ] || export XFITTER_COMMIT

# 1) Base LCG environment from CVMFS. The override is primarily useful for
# testing and for installations providing an equivalent site-local setup.
LCG_SETUP="${XFITTER_LCG_SETUP:-/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/setup.sh}"
[ -r "$LCG_SETUP" ] || {
    fail_setup "cannot read $LCG_SETUP"
    return 1 2>/dev/null || exit 1
}
source "$LCG_SETUP" || {
    fail_setup "failed to source $LCG_SETUP"
    return 1 2>/dev/null || exit 1
}

# 2) Source the xFitter setup from NFS location (accessible to Condor workers)
# Worktrees are relative to XFITTER_ROOT; setup.sh and dependencies may live in
# a separate XFITTER_SETUP_ROOT. Keep the old flat layout as the fallback.
# Source from that directory for setup scripts that read files relative to PWD.
: "${XFITTER_ROOT:?Set XFITTER_ROOT in .env at the repo root}"
export XFITTER_SETUP_ROOT="${XFITTER_SETUP_ROOT:-$XFITTER_ROOT}"
XFITTER_SETUP="$XFITTER_SETUP_ROOT/setup.sh"
[ -r "$XFITTER_SETUP" ] || {
    fail_setup "cannot read $XFITTER_SETUP"
    return 1 2>/dev/null || exit 1
}

pushd "$XFITTER_SETUP_ROOT" > /dev/null || {
    fail_setup "cannot cd to $XFITTER_SETUP_ROOT"
    return 1 2>/dev/null || exit 1
}
source "$XFITTER_SETUP" || {
    popd > /dev/null
    fail_setup "failed to source $XFITTER_SETUP"
    return 1 2>/dev/null || exit 1
}
popd > /dev/null || {
    fail_setup "failed to return from $XFITTER_SETUP_ROOT"
    return 1 2>/dev/null || exit 1
}

# 3) Optional: select a specific xFitter build tree (git worktree) instead of
# the general-purpose default baked into $XFITTER_SETUP_ROOT/setup.sh
# (xfitter-master). Set XFITTER_TREE in .env or the environment to:
#   - a directory name under $XFITTER_ROOT, e.g. XFITTER_TREE=xfitter-bartlett-fixes
#   - an absolute path to a built tree
# Leave it unset/empty to keep the default. Each tree's xfitter binary carries
# an absolute RPATH to its own lib/xfitter modules, so prepending its bin/ (and
# lib/) is enough to run that build; deps are shared across trees.
if [ -n "${XFITTER_TREE:-}" ]; then
    case "$XFITTER_TREE" in
        /*) _xf_tree="$XFITTER_TREE" ;;
        *)  _xf_tree="$XFITTER_ROOT/$XFITTER_TREE" ;;
    esac
    # Hard stop rather than silent fallback to the default tree: if the tree was
    # requested explicitly it must be built, else the run would use the wrong
    # binary. fail_setup's return is swallowed inside its function when sourced,
    # so abort here at top level.
    if [ ! -x "$_xf_tree/bin/xfitter" ]; then
        echo "setup-env.sh: XFITTER_TREE=$XFITTER_TREE: no built xfitter at $_xf_tree/bin/xfitter" >&2
        unset _xf_tree
        return 1 2>/dev/null || exit 1
    fi
    export PATH="$_xf_tree/bin:$PATH"
    export LD_LIBRARY_PATH="$_xf_tree/lib:$_xf_tree/lib/xfitter:${LD_LIBRARY_PATH}"
    unset _xf_tree
fi

# 4) Resolve the build actually selected above and, when requested, enforce an
# exact Git commit. XFITTER_COMMIT must be a full 40-character SHA-1; branch
# names and abbreviated hashes are intentionally rejected because they are not
# immutable pins. Generated Condor workers export this value before sourcing
# setup-env.sh, so a moved/reused build directory fails before xFitter starts.
if ! _xf_bin="$(command -v xfitter 2>/dev/null)" || [ -z "$_xf_bin" ]; then
    echo "setup-env.sh: xfitter is not on PATH after environment setup" >&2
    unset _xf_bin
    return 1 2>/dev/null || exit 1
fi
if ! _xf_selected_tree="$(cd "$(dirname "$_xf_bin")/.." && pwd)"; then
    echo "setup-env.sh: cannot resolve the selected xFitter tree from $_xf_bin" >&2
    unset _xf_bin _xf_selected_tree
    return 1 2>/dev/null || exit 1
fi
if [ -n "${XFITTER_COMMIT:-}" ]; then
    if [[ ! "$XFITTER_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
        echo "setup-env.sh: XFITTER_COMMIT must be a full lowercase 40-character Git SHA-1" >&2
        unset _xf_bin _xf_selected_tree
        return 1 2>/dev/null || exit 1
    fi
    if ! _xf_actual_commit="$(git -C "$_xf_selected_tree" rev-parse --verify HEAD 2>/dev/null)" || [ -z "$_xf_actual_commit" ]; then
        echo "setup-env.sh: cannot determine Git HEAD for $_xf_selected_tree" >&2
        unset _xf_bin _xf_selected_tree _xf_actual_commit
        return 1 2>/dev/null || exit 1
    fi
    if [ "$_xf_actual_commit" != "$XFITTER_COMMIT" ]; then
        echo "setup-env.sh: xFitter commit mismatch for $_xf_selected_tree" >&2
        echo "setup-env.sh: expected $XFITTER_COMMIT, found $_xf_actual_commit" >&2
        unset _xf_bin _xf_selected_tree _xf_actual_commit
        return 1 2>/dev/null || exit 1
    fi
    if ! _xf_tracked_changes="$(git -C "$_xf_selected_tree" status --porcelain --untracked-files=no 2>/dev/null)"; then
        echo "setup-env.sh: cannot inspect tracked changes in $_xf_selected_tree" >&2
        unset _xf_bin _xf_selected_tree _xf_actual_commit _xf_tracked_changes
        return 1 2>/dev/null || exit 1
    fi
    if [ -n "$_xf_tracked_changes" ]; then
        echo "setup-env.sh: selected xFitter tree has tracked changes despite its commit pin:" >&2
        printf '%s\n' "$_xf_tracked_changes" >&2
        unset _xf_bin _xf_selected_tree _xf_actual_commit _xf_tracked_changes
        return 1 2>/dev/null || exit 1
    fi
    echo "setup-env.sh: verified xFitter commit $_xf_actual_commit" >&2
    unset _xf_actual_commit _xf_tracked_changes
fi
echo "setup-env.sh: using xFitter tree $_xf_selected_tree ($_xf_bin)" >&2
unset _xf_bin _xf_selected_tree
