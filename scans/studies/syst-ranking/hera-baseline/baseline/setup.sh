#!/bin/bash
# Setup script for hera-baseline systematic-ranking study
# Creates symlinks to run-scan and plot commands

cd "$(dirname "$0")"

# Create symlinks
ln -sf ../../../../bin/run-scan run-scan
ln -sf ../../../../bin/plot plot

# Make executable
chmod +x run-scan plot

echo "✓ Symlinks created:"
ls -la run-scan plot

echo ""
echo "Ready to use! Try:"
echo "  ./run-scan --dry-run"
