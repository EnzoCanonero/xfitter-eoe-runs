#!/bin/bash
# Create a new xfitter fit directory.
# Usage: ./new_fit.sh <name-or-nested-path> [template_dir]
#
# template_dir defaults to the errors-on-errors example.

set -e

BASEDIR="$(cd "$(dirname "$0")" && pwd)"
NAME="$1"
TEMPLATE="${2:-/home/ecanoner/PDF/xfitter-master/examples/errors-on-errors}"

if [ -z "$NAME" ]; then
    echo "Usage: $0 <name> [template_dir]"
    exit 1
fi

FITDIR="$BASEDIR/fits/$NAME"

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

# Create subdirectories (also creates nested parents in fits/)
mkdir -p "$FITDIR/config" "$FITDIR/condor/logs"

# Copy editable config files
for f in steering.txt parameters.yaml; do
    if [ -f "$TEMPLATE/$f" ]; then
        cp "$TEMPLATE/$f" "$FITDIR/config/"
    fi
done

# Symlink read-only shared files into config/
for f in constants.yaml unpolarised.wgt; do
    if [ -f "$TEMPLATE/$f" ]; then
        ln -sf "$TEMPLATE/$f" "$FITDIR/config/$f"
    fi
done

# Symlink shared datafiles into fit root (absolute works for any depth)
ln -sfn "$BASEDIR/datafiles" "$FITDIR/datafiles"

# Generate condor/run_fit.sh
cat > "$FITDIR/condor/run_fit.sh" << RUNEOF
#!/bin/bash
FITDIR="$FITDIR"
source "$BASEDIR/setup_env.sh"
cd "\$FITDIR"

# Stage config files into CWD for xfitter
for f in config/*; do
    ln -sf "\$f" .
done

xfitter
rc=\$?

# Clean up staged symlinks
for f in config/*; do
    rm -f "\$(basename "\$f")"
done

exit \$rc
RUNEOF
chmod +x "$FITDIR/condor/run_fit.sh"

# Generate condor/job.sub
cat > "$FITDIR/condor/job.sub" << SUBEOF
universe            = vanilla
executable          = condor/run_fit.sh
output              = condor/logs/output.log
error               = condor/logs/error.log
log                 = condor/logs/run.log
should_transfer_files = NO
initialdir          = $FITDIR
queue 1
SUBEOF

echo ""
echo "Done. To run:"
echo "  cd $FITDIR"
echo "  condor_submit condor/job.sub"
echo ""
echo "Edit configs in: $FITDIR/config/"
