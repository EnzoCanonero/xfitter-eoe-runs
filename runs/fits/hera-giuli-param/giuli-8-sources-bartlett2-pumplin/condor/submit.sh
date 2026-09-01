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
[ -x "$REPO_ROOT/scripts/fix-lhapdf-info" ] || {
    echo "Cannot find executable scripts/fix-lhapdf-info" >&2
    exit 1
}

mkdir -p "$DIR/logs" "$FIT_DIR/output"

# ── Generate run_fit.sh ──────────────────────────────────────
cat > "$DIR/run_fit.sh" << EOF
#!/bin/bash
set -e
export HOME="\${HOME:-/tmp}"
export XFITTER_TREE=xfitter-bartlett-fixes
source "$REPO_ROOT/scripts/setup-env.sh"

# Record the exact executable and libraries used by the fit.
XFITTER_BIN=\$(command -v xfitter)
XFITTER_TREE_DIR=\$(cd "\$(dirname "\$XFITTER_BIN")/.." && pwd)
{
  echo "binary=\$XFITTER_BIN"
  echo "git_commit=\$(git -C "\$XFITTER_TREE_DIR" rev-parse HEAD 2>/dev/null || echo unavailable)"
  if [ -n "\$(git -C "\$XFITTER_TREE_DIR" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
    echo "git_dirty=true"
  else
    echo "git_dirty=false"
  fi
  find "\$XFITTER_TREE_DIR/bin" "\$XFITTER_TREE_DIR/lib/xfitter" \
       -maxdepth 1 -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum
  sha256sum "\$XFITTER_TREE_DIR/lib/libxfitter.so"
} > "$DIR/logs/xfitter_provenance.txt"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=\$(mktemp -d)
trap "rm -rf \$SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \\
      "\$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="\$SHIM_DIR:\$LD_LIBRARY_PATH"

cd "$FIT_DIR/config"
xfitter
"$REPO_ROOT/scripts/fix-lhapdf-info" "$FIT_DIR"
cp "$DIR/logs/xfitter_provenance.txt" \
   "$FIT_DIR/output/xfitter_provenance.txt"
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
