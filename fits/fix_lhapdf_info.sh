#!/bin/bash
# Correct NumMembers + ErrorType in an xFitter-written LHAPDF6 proton.info.
#
# Why: xFitter's getErrorType()/getNmembers() (src/lhapdf6_output.cc) compare the
# `doErrors` value against the exact strings "Pumplin"/"Hesse". Our configs use a
# multiline doErrors block ("Pumplin\nSET ERRDEF 0.5\nITERATE 10"), so the match
# fails and the .info is written with NumMembers:1 / ErrorType:symmhessian even
# though the Pumplin step produced 1+2N real member files. LHAPDF then loads only
# member 0 -> no error band. This sets NumMembers to the true count and
# ErrorType:hessian (Pumplin writes asymmetric +/- eigenvector pairs).
#
# Usage: fix_lhapdf_info.sh <fit-dir-or-proton-dir> [more ...]
#   e.g. fix_lhapdf_info.sh hera/hera-baseline/baseline-7-sources
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
    sed -i -E "s/^NumMembers:.*/NumMembers: $n/; s/^ErrorType:.*/ErrorType: hessian/" \
        "$pdir/proton.info"
    echo "$pdir -> NumMembers: $n, ErrorType: hessian"
done
