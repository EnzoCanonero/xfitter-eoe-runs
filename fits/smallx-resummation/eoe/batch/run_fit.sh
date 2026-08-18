#!/bin/bash
set -eo pipefail

FIT_DIR="${1:?fit directory is required}"
REPO_ROOT=/nfs/scratch2/ecanoner/xfitter-eoe-runs
LHAPDF_INFO_FIXER="$REPO_ROOT/fits/fix_lhapdf_info.sh"
EXPECTED_MEMBERS=47
EXPECTED_PAIRS=23

if [ ! -x "$LHAPDF_INFO_FIXER" ]; then
    echo "Missing or non-executable LHAPDF metadata fixer: $LHAPDF_INFO_FIXER" >&2
    exit 2
fi

export XFITTER_TREE=xfitter-bartlett-apfel306-hell3
source "$REPO_ROOT/setup_env.sh"

XFITTER_BIN=$(command -v xfitter)
XFITTER_TREE_DIR=$(cd "$(dirname "$XFITTER_BIN")/.." && pwd)
EXPECTED_TREE=/nfs/scratch2/ecanoner/PDF/xfitter-bartlett-apfel306-hell3

if [ "$XFITTER_TREE_DIR" != "$EXPECTED_TREE" ]; then
    echo "Unexpected xFitter tree: $XFITTER_TREE_DIR" >&2
    exit 3
fi

APFEL_MODULE="$XFITTER_TREE_DIR/lib/xfitter/libevolutionAPFEL.so"
APFEL_LIB=$(ldd "$APFEL_MODULE" | awk '$1 ~ /^libAPFEL/ {print $3; exit}')
case "$APFEL_LIB" in
    /nfs/scratch2/ecanoner/PDF/deps/apfel/lib/*) ;;
    *)
        echo "Unexpected APFEL library: ${APFEL_LIB:-not resolved}" >&2
        exit 4
        ;;
esac

APFEL_VERSION=$(/nfs/scratch2/ecanoner/PDF/deps/apfel/bin/apfel-config --version)
if [ "$APFEL_VERSION" != "3.0.6" ]; then
    echo "Unexpected APFEL version: $APFEL_VERSION" >&2
    exit 5
fi

mkdir -p "$FIT_DIR/condor/logs"
PROVENANCE_LOG="$FIT_DIR/condor/logs/xfitter_provenance.txt"
{
    echo "binary=$XFITTER_BIN"
    echo "git_commit=$(git -C "$XFITTER_TREE_DIR" rev-parse HEAD 2>/dev/null || echo unavailable)"
    if [ -n "$(git -C "$XFITTER_TREE_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        echo "git_dirty=true"
    else
        echo "git_dirty=false"
    fi
    echo "apfel_library=$APFEL_LIB"
    echo "apfel_version=$APFEL_VERSION"
    find "$XFITTER_TREE_DIR/bin" "$XFITTER_TREE_DIR/lib/xfitter" \
        -maxdepth 1 -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum
    sha256sum "$XFITTER_TREE_DIR/lib/libxfitter.so" "$APFEL_LIB"
    echo "[APFEL module linkage]"
    ldd "$APFEL_MODULE"
} > "$PROVENANCE_LOG"

# Condor workers do not provide libflexiblas; use the established OpenBLAS shim.
SHIM_DIR=$(mktemp -d)
trap 'rm -rf "$SHIM_DIR"' EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \
    "$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="$SHIM_DIR:$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
RUN_LOG="$FIT_DIR/condor/logs/xfitter_run.log"
xfitter 2>&1 | tee "$RUN_LOG"

# Some legacy HELL failures return a zero process status, so inspect the log as
# well as the exit code before accepting the job.
if grep -Eqi 'HELLx: Error|Fortran runtime error|symbol lookup error|error while loading shared libraries' "$RUN_LOG"; then
    echo "Fatal runtime signature found in $RUN_LOG" >&2
    exit 6
fi

if [ ! -s "$FIT_DIR/output/Results.txt" ] || [ ! -s "$FIT_DIR/output/minuit.out.txt" ]; then
    echo "Missing central fit output for $FIT_DIR" >&2
    exit 7
fi

if [ "$(tr -d '[:space:]' < "$FIT_DIR/output/Status.out")" != "OK" ]; then
    echo "xFitter did not report Status.out=OK for $FIT_DIR" >&2
    exit 8
fi

if ! grep -q 'MIGRAD MINIMIZATION HAS CONVERGED' "$FIT_DIR/output/minuit.out.txt"; then
    echo "MIGRAD did not report convergence for $FIT_DIR" >&2
    exit 9
fi

if ! grep -q 'ITERATE finished' "$FIT_DIR/output/minuit.out.txt" || \
   ! grep -q 'ERROR MATRIX FROM ITERATE' "$FIT_DIR/output/minuit.out.txt"; then
    echo "Pumplin ITERATE output is incomplete for $FIT_DIR" >&2
    exit 10
fi

plus_pairs=$(find "$FIT_DIR/output" -maxdepth 1 -name 'pdfs_q2val_s??p_01.txt' | wc -l)
minus_pairs=$(find "$FIT_DIR/output" -maxdepth 1 -name 'pdfs_q2val_s??m_01.txt' | wc -l)
if [ "$plus_pairs" -ne "$EXPECTED_PAIRS" ] || [ "$minus_pairs" -ne "$EXPECTED_PAIRS" ]; then
    echo "Expected $EXPECTED_PAIRS Pumplin pairs, found +$plus_pairs/-$minus_pairs" >&2
    exit 11
fi

if [ ! -s "$FIT_DIR/output/proton/proton.info" ]; then
    echo "Missing or empty LHAPDF metadata for $FIT_DIR" >&2
    exit 12
fi

# Repair the metadata written for the multiline doErrors block.
"$LHAPDF_INFO_FIXER" "$FIT_DIR"

member_count=$(find "$FIT_DIR/output/proton" -maxdepth 1 -name 'proton_*.dat' | wc -l)
info_members=$(awk '/^NumMembers:/ {print $2}' "$FIT_DIR/output/proton/proton.info")
info_type=$(awk '/^ErrorType:/ {print $2}' "$FIT_DIR/output/proton/proton.info")
if [ "$member_count" -ne "$EXPECTED_MEMBERS" ] || \
   [ "$info_members" != "$EXPECTED_MEMBERS" ] || [ "$info_type" != "hessian" ]; then
    echo "Invalid LHAPDF set: files=$member_count metadata=$info_members type=$info_type" >&2
    exit 13
fi

cp "$PROVENANCE_LOG" "$FIT_DIR/output/xfitter_provenance.txt"
cp "$RUN_LOG" "$FIT_DIR/output/xfitter_run.log"
