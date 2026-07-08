#!/bin/bash
# Generate condor scripts with correct absolute paths and submit.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
FIT_DIR="$(cd "$DIR/.." && pwd)"

# Find setup_env.sh at the repo root
REPO_ROOT="$DIR"
while [ ! -f "$REPO_ROOT/setup_env.sh" ] && [ "$REPO_ROOT" != "/" ]; do
    REPO_ROOT="$(dirname "$REPO_ROOT")"
done
[ -f "$REPO_ROOT/setup_env.sh" ] || { echo "Cannot find setup_env.sh" >&2; exit 1; }

mkdir -p "$DIR/logs" "$FIT_DIR/output"

# ── Generate run_fit.sh ──────────────────────────────────────
cat > "$DIR/run_fit.sh" << EOF
#!/bin/bash
set -e
export HOME="\${HOME:-/tmp}"
source "$REPO_ROOT/setup_env.sh"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=\$(mktemp -d)
trap "rm -rf \$SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \
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
request_memory      = 2GB
queue 1
EOF

# ── Set OutputDirectory in parameters.yaml ───────────────────
sed -i "s|^OutputDirectory:.*|OutputDirectory: \"$FIT_DIR/output\"|" "$FIT_DIR/config/parameters.yaml"

# ── Submit ───────────────────────────────────────────────────
condor_submit "$DIR/job.sub"
