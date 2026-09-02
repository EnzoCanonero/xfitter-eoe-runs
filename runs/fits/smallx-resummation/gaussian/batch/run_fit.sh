#!/bin/bash
set -eo pipefail

FIT_DIR="${1:?fit directory is required}"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$REPO_ROOT/scripts/setup-env.sh" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -f "$REPO_ROOT/scripts/setup-env.sh" ] || {
    echo "Cannot find scripts/setup-env.sh" >&2
    exit 2
}
LHAPDF_INFO_FIXER="$REPO_ROOT/scripts/fix-lhapdf-info"

if [ ! -x "$LHAPDF_INFO_FIXER" ]; then
    echo "Missing or non-executable LHAPDF metadata fixer: $LHAPDF_INFO_FIXER" >&2
    exit 2
fi

export XFITTER_TREE=xfitter-bartlett-apfel306-hell3
source "$REPO_ROOT/scripts/setup-env.sh"

XFITTER_BIN=$(command -v xfitter)
XFITTER_TREE_DIR=$(cd "$(dirname "$XFITTER_BIN")/.." && pwd)
EXPECTED_TREE=/nfs/scratch2/ecanoner/PDF/xfitter-bartlett-apfel306-hell3

if [ "$XFITTER_TREE_DIR" != "$EXPECTED_TREE" ]; then
    echo "Unexpected xFitter tree: $XFITTER_TREE_DIR" >&2
    exit 2
fi

APFEL_MODULE="$XFITTER_TREE_DIR/lib/xfitter/libevolutionAPFEL.so"
APFEL_LIB=$(ldd "$APFEL_MODULE" | awk '$1 ~ /^libAPFEL/ {print $3; exit}')
case "$APFEL_LIB" in
    /nfs/scratch2/ecanoner/PDF/deps/apfel/lib/*) ;;
    *)
        echo "Unexpected APFEL library: ${APFEL_LIB:-not resolved}" >&2
        exit 3
        ;;
esac

mkdir -p "$FIT_DIR/output" "$FIT_DIR/condor/logs"
{
    echo "binary=$XFITTER_BIN"
    echo "git_commit=$(git -C "$XFITTER_TREE_DIR" rev-parse HEAD 2>/dev/null || echo unavailable)"
    if [ -n "$(git -C "$XFITTER_TREE_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        echo "git_dirty=true"
    else
        echo "git_dirty=false"
    fi
    echo "apfel_library=$APFEL_LIB"
    echo "apfel_version=$(/nfs/scratch2/ecanoner/PDF/deps/apfel/bin/apfel-config --version)"
    find "$XFITTER_TREE_DIR/bin" "$XFITTER_TREE_DIR/lib/xfitter" \
        -maxdepth 1 -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum
    sha256sum "$APFEL_LIB"
    echo "[APFEL module linkage]"
    ldd "$APFEL_MODULE"
} > "$FIT_DIR/output/xfitter_provenance.txt"

# Condor workers do not provide libflexiblas; use the established OpenBLAS shim.
SHIM_DIR=$(mktemp -d)
trap 'rm -rf "$SHIM_DIR"' EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \
    "$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="$SHIM_DIR:$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
RUN_LOG="$FIT_DIR/output/xfitter_run.log"
xfitter 2>&1 | tee "$RUN_LOG"

# Some legacy HELL failures return a zero process status, so inspect the log as
# well as the exit code before accepting the job.
if grep -Eqi 'HELLx: Error|Fortran runtime error|symbol lookup error|error while loading shared libraries' "$RUN_LOG"; then
    echo "Fatal runtime signature found in $RUN_LOG" >&2
    exit 4
fi

if [ ! -s "$FIT_DIR/output/Results.txt" ]; then
    echo "Missing or empty Results.txt for $FIT_DIR" >&2
    exit 5
fi

if [ ! -s "$FIT_DIR/output/proton/proton.info" ]; then
    echo "Missing or empty LHAPDF metadata for $FIT_DIR" >&2
    exit 6
fi

# Repair the LHAPDF member count/type written for multiline doErrors blocks.
"$LHAPDF_INFO_FIXER" "$FIT_DIR"
