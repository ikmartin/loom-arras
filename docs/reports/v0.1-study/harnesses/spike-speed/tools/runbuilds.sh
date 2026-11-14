#!/bin/bash
# Each change's save-build on relloc-b, in process, one code tree after another; two rounds, the second in reverse order.
SP=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/spike-speed
export XDG_CONFIG_HOME=$SP/xdg
Q=$SP/relloc-b
OUT=$SP/logs/builds.jsonl
run() { # label tree commit flags...
  local label=$1 tree=$2 commit=$3; shift 3
  if [ "$tree" = stage ]; then git -C $SP/stage checkout -q --detach $commit; fi
  $SP/$tree/loom/.venv/bin/python $SP/tools/builds.py $Q $label "$@" >> $OUT 2>> $SP/logs/builds.err
}
CONFIGS=(
"A-base-cg repo - --cache-git"
"B-c1-cg stage d1d96cc4 --cache-git"
"C-c2-cg stage 99356fa4 --cache-git --previews-tex 0"
"D-base-nocg repo -"
"E-c3-nocg stage e0185403 --previews-tex 0"
"F-c3-notex stage e0185403 --tex 0 --previews-tex 0"
)
for c in "${CONFIGS[@]}"; do run $c --n ${N:-3}; done
if [ -n "$ROUND2" ]; then for ((i=${#CONFIGS[@]}-1; i>=0; i--)); do run ${CONFIGS[$i]} --n ${N:-3}; done; fi
