#!/bin/bash
# Setup script for hera-baseline likelihood-scan study
cd "$(dirname "$0")"
ln -sf ../../../../bin/run-scan run-scan
ln -sf ../../../../bin/plot plot
chmod +x run-scan plot
echo "Symlinks created:"
ls -la run-scan plot
echo ""
echo "Ready to use! Try:"
echo "  ./run-scan --dry-run"
