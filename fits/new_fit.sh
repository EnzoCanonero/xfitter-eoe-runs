#!/bin/bash
# Create a new xfitter fit directory.
# Usage: ./new_fit.sh <path> [template_dir]
#
# path:         Nested path under fits/ (e.g. hera/my-study/variant-a)
# template_dir: Directory containing steering.txt and parameters.yaml.
#               Can be an existing fit's config/ dir or an xfitter example dir.
#               Defaults to hera/hera-baseline/eoe/config/ (relative to fits/).

set -e

FITSDIR="$(cd "$(dirname "$0")" && pwd)"
BASEDIR="$(dirname "$FITSDIR")"
NAME="$1"
TEMPLATE="${2:-$FITSDIR/hera/hera-baseline/eoe/config}"

# Resolve relative template paths against FITSDIR
if [ "${TEMPLATE:0:1}" != "/" ]; then
    TEMPLATE="$FITSDIR/$TEMPLATE"
fi

if [ -z "$NAME" ]; then
    echo "Usage: $0 <path> [template_dir]"
    echo ""
    echo "  path:         Nested path under fits/ (e.g. hera/my-study/variant-a)"
    echo "  template_dir: Directory with steering.txt + parameters.yaml (default: eoe config)"
    echo ""
    echo "Examples:"
    echo "  $0 hera/my-study/variant-a"
    echo "  $0 hera/my-study/variant-b hera/hera-baseline/nominal/config"
    exit 1
fi

FITDIR="$FITSDIR/$NAME"
CONFIGDIR="$FITDIR/config"

if [ ! -d "$TEMPLATE" ]; then
    echo "Error: template directory not found: $TEMPLATE"
    exit 1
fi

if [ -d "$FITDIR" ]; then
    echo "Error: $FITDIR already exists"
    exit 1
fi

echo "Creating fit: $FITDIR"
echo "Template:     $TEMPLATE"

# ── 1. Create directory structure ────────────────────────────
mkdir -p "$CONFIGDIR" "$FITDIR/condor/logs" "$FITDIR/output"

# ── 2. Copy editable config files ───────────────────────────
for f in steering.txt parameters.yaml; do
    if [ -f "$TEMPLATE/$f" ]; then
        cp "$TEMPLATE/$f" "$CONFIGDIR/"
    fi
done

# ── 3. Copy read-only shared files into config/ ─────────────
for f in constants.yaml unpolarised.wgt; do
    src="$TEMPLATE/$f"
    # Resolve symlinks so we copy the real file
    if [ -L "$src" ]; then
        src="$(readlink -f "$src")"
    fi
    if [ -f "$src" ]; then
        cp "$src" "$CONFIGDIR/$f"
    fi
done

# ── 4. Copy data files into config/ ─────────────────────────
# Parse steering.txt for InputFileNames and copy the .dat files
DATAROOT="$BASEDIR/datafiles"
if [ -f "$CONFIGDIR/steering.txt" ]; then
    while IFS= read -r line; do
        # Extract filename between single quotes ending in .dat
        fname=$(echo "$line" | grep -oP "'\K[^']*\.dat" || true)
        if [ -n "$fname" ]; then
            base=$(basename "$fname")
            # Find the file in datafiles/
            src=$(find -L "$DATAROOT" -name "$base" -type f 2>/dev/null | head -1)
            if [ -n "$src" ]; then
                cp "$src" "$CONFIGDIR/$base"
            else
                echo "Warning: data file not found in datafiles/: $base"
            fi
        fi
    done < "$CONFIGDIR/steering.txt"
fi

# ── 5. Convert data paths in steering.txt to bare filenames ─
# Replace 'path/to/file.dat' with 'file.dat'
if [ -f "$CONFIGDIR/steering.txt" ]; then
    sed -i "s|'[^']*\/\([^']*\.dat\)'|'\1'|g" "$CONFIGDIR/steering.txt"
fi

# ── 6. Add OutputDirectory to parameters.yaml ───────────────
if [ -f "$CONFIGDIR/parameters.yaml" ]; then
    # Remove any existing OutputDirectory line
    sed -i '/^OutputDirectory:/d' "$CONFIGDIR/parameters.yaml"
    # Remove any comment line immediately before it
    sed -i '/^# Output directory.*xfitter/d' "$CONFIGDIR/parameters.yaml"
    cat >> "$CONFIGDIR/parameters.yaml" << EOF

# Output directory (absolute path so xfitter writes here regardless of CWD)
OutputDirectory: "$FITDIR/output"
EOF
fi

# ── 7. Generate condor/run_fit.sh ───────────────────────────
cat > "$FITDIR/condor/run_fit.sh" << RUNEOF
#!/bin/bash
# xFitter fit execution script
set -e

CONFIGDIR="$CONFIGDIR"
source "$BASEDIR/setup_env.sh"

# flexiblas shim (condor nodes miss libflexiblas, map to openblas)
SHIM_DIR=\$(mktemp -d)
trap "rm -rf \$SHIM_DIR" EXIT
ln -s /cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/lib/libopenblas.so \\
      "\$SHIM_DIR/libflexiblas.so.3"
export LD_LIBRARY_PATH="\$SHIM_DIR:\$LD_LIBRARY_PATH"

cd "\$CONFIGDIR"
xfitter
RUNEOF
chmod +x "$FITDIR/condor/run_fit.sh"

# ── 8. Generate condor/job.sub ──────────────────────────────
cat > "$FITDIR/condor/job.sub" << SUBEOF
universe            = vanilla
executable          = $FITDIR/condor/run_fit.sh
output              = $FITDIR/condor/logs/output.log
error               = $FITDIR/condor/logs/error.log
log                 = $FITDIR/condor/logs/run.log
should_transfer_files = NO
initialdir          = $CONFIGDIR
request_cpus        = 1
request_memory      = 2GB
queue 1
SUBEOF

echo ""
echo "Done. Structure:"
echo "  $FITDIR/"
echo "    config/    -- steering.txt, parameters.yaml, data symlinks"
echo "    condor/    -- run_fit.sh, job.sub, logs/"
echo "    output/    -- (xfitter writes here)"
echo ""
echo "To run:"
echo "  condor_submit $FITDIR/condor/job.sub"
echo ""
echo "Edit configs in: $CONFIGDIR/"
