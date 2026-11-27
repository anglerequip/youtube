#!/bin/bash
# Cloud test render of "The Lure Avalanche" (Linux, no GPU). Usage: bash tools/blender/omega/cloud_render.sh <blender> <out> [frames a,b] [extra]
# The repo bundle assets/omega holds the rigs, CC0 textures/anim, the sheet head image and the phone screen (kit.asset maps them).
set -e
B=${1:?blender binary}; O=${2:?out dir}; FR=${3:-1,240}; R=$(cd "$(dirname "$0")/../../.." && pwd)
export OMEGA_ROOT=$R/assets/omega
mkdir -p $O; date +%s > $O/t0
"$B" -b -P $R/tools/blender/omega/lure30.py -- --nils $OMEGA_ROOT/nils_rig.blend --theo $OMEGA_ROOT/theo_rig.blend \
  --timeline $OMEGA_ROOT/timeline.json --out $O --pct 50 --samples 32 --mocap --sheetface --frames $FR ${4:-} > $O/render.log 2>&1
date +%s > $O/t1; echo "seconds: $(( $(cat $O/t1) - $(cat $O/t0) ))"; ls $O/frames | wc -l
