#!/bin/bash
# Correct NumMembers + ErrorType in an xFitter-written LHAPDF6 proton.info.
#
# Why: xFitter's getErrorType()/getNmembers() (src/lhapdf6_output.cc) compare the
# `doErrors` value against the exact strings "Pumplin"/"Hesse". Our configs use a
# multiline doErrors block ("Pumplin\nSET ERRDEF 0.5\nITERATE 10"), so the match
# fails and the .info is written with NumMembers:1 / ErrorType:symmhessian even
# though the band step produced the real member files. LHAPDF then loads only
# member 0 -> no error band. This sets NumMembers to the true count and the
# ErrorType matching the band method actually used:
#   - Pumplin/ITERATE writes +/- eigenvector PAIRS  (pdfs_q2val_s01p_/s01m_)
#       -> ErrorType: hessian      (pair formula)
#   - Hesse/ErrBandsSym writes SINGLE symmetric displacements (pdfs_q2val_s01s_)
#       -> ErrorType: symmhessian  (sum-of-squares formula)
# Mislabelling a Hesse set as 'hessian' makes consumers pair up unrelated
# eigenvectors and underestimate the band by ~1/sqrt(2).
#
# Usage: fix_lhapdf_info.sh <fit-dir-or-proton-dir> [more ...]
#   e.g. fix_lhapdf_info.sh hera-baseline/baseline-7-sources
set -e
for arg in "$@"; do
    if   [ -f "$arg/proton.info" ];               then pdir="$arg"
    elif [ -f "$arg/output/proton/proton.info" ]; then pdir="$arg/output/proton"
    else echo "skip: no proton.info under $arg" >&2; continue
    fi
    n=$(ls "$pdir"/proton_*.dat 2>/dev/null | wc -l)
    if [ "$n" -lt 2 ]; then
        echo "$pdir: $n member(s) - not a multi-member set, left as-is"
        continue
    fi
    outdir=$(dirname "$pdir")
    if ls "$outdir"/pdfs_q2val_s[0-9][0-9]m_* >/dev/null 2>&1; then
        etype=hessian          # +/- pairs (Pumplin/ITERATE)
    elif ls "$outdir"/pdfs_q2val_s[0-9][0-9]s_* >/dev/null 2>&1; then
        etype=symmhessian      # single symmetric displacements (Hesse)
    else
        etype=hessian
        echo "$pdir: WARNING no band grid files found, assuming hessian" >&2
    fi
    sed -i -E "s/^NumMembers:.*/NumMembers: $n/; s/^ErrorType:.*/ErrorType: $etype/" \
        "$pdir/proton.info"
    echo "$pdir -> NumMembers: $n, ErrorType: $etype"
done
