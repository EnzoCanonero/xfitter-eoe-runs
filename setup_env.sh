#!/bin/bash
# Source this to set up the environment for xfitter runs.
# Used by condor job scripts and for interactive testing.

export XFITTER_HOME=/home/ecanoner/PDF/xfitter-master
export PATH=$XFITTER_HOME/bin:$PATH
export LD_LIBRARY_PATH=$XFITTER_HOME/lib:$XFITTER_HOME/lib/xfitter:/home/ecanoner/PDF/deps/qcdnum/lib:/home/ecanoner/PDF/deps/lhapdf/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
