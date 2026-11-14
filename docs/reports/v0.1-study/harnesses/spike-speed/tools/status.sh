#!/bin/bash
# `loom status` as an agent calls it, alternating code trees: usage status.sh QUILT TREE...
SP=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/spike-speed
export XDG_CONFIG_HOME=$SP/xdg AI_AGENT=1
Q=$1; shift
cd $Q || exit 1
for i in 1 2 3; do for tree in "$@"; do
  s=$(python3 -c 'import time; print(time.time())')
  $SP/$tree/loom/.venv/bin/loom status > /dev/null 2>&1; rc=$?
  e=$(python3 -c 'import time; print(time.time())')
  L=$(sysctl -n vm.loadavg | tr -d '{}')
  python3 -c "print('$tree', round($e-$s, 2), 'rc=$rc', 'load', '$L')"
done; done
