#!/bin/bash
# Generate condor scripts with correct absolute paths and submit.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
FIT_DIR="$(cd "$DIR/.." && pwd)"

# Find scripts/setup-env.sh at the repo root
REPO_ROOT="$DIR"
while [ ! -f "$REPO_ROOT/scripts/setup-env.sh" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -f "$REPO_ROOT/scripts/setup-env.sh" ] || { echo "Cannot find scripts/setup-env.sh" >&2; exit 1; }

# Restore ignored dataset copies when launching from a fresh checkout.
# Keep bare input filenames so xFitter dataset IDs match the validated runs.
FIT_DATA_ROOT="$REPO_ROOT/datasets/hera/h1zeusCombined/inclusiveDis/1506.06042"
for FIT_DATA_FILE in 'HERA1+2_NCep_920-thexp.dat' 'HERA1+2_NCep_820-thexp.dat' 'HERA1+2_NCep_575-thexp.dat' 'HERA1+2_NCep_460-thexp.dat' 'HERA1+2_NCem-thexp.dat' 'HERA1+2_CCep-thexp.dat' 'HERA1+2_CCem-thexp.dat'; do
    if [ ! -f "$FIT_DIR/config/$FIT_DATA_FILE" ]; then
        cp -- "$FIT_DATA_ROOT/$FIT_DATA_FILE" "$FIT_DIR/config/$FIT_DATA_FILE"
    fi
done

mkdir -p "$DIR/logs" "$FIT_DIR/output"

# ── Generate run_fit.sh ──────────────────────────────────────
cat > "$DIR/run_fit.sh" << EOF
#!/bin/bash
set -e
export XFITTER_TREE=merge-master/xfitter-master
# export XFITTER_COMMIT=aead2b830305623b73709f748a4db918a0bf136c
source "$REPO_ROOT/scripts/setup-env.sh"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=\$(mktemp -d)
trap "rm -rf \$SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \\
      "\$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="\$SHIM_DIR:\$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
xfitter
EOF
chmod +x "$DIR/run_fit.sh"

# ── Generate job.sub ─────────────────────────────────────────
cat > "$DIR/job.sub" << EOF
universe            = vanilla
executable          = $DIR/run_fit.sh
output              = $DIR/logs/output.log
error               = $DIR/logs/error.log
log                 = $DIR/logs/run.log
should_transfer_files = NO
initialdir          = $FIT_DIR/config
request_cpus        = 1
request_memory      = 4GB
queue 1
EOF

# ── Set OutputDirectory in parameters.yaml ───────────────────
sed -i "s|^OutputDirectory:.*|OutputDirectory: \"$FIT_DIR/output\"|" "$FIT_DIR/config/parameters.yaml"

# ── Submit ───────────────────────────────────────────────────
condor_submit "$DIR/job.sub"
