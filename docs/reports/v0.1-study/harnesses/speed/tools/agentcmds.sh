#!/bin/bash
# Time the agent-facing commands three times each in quilt $1; prints "seconds  command".
Q="$1"; L=/Users/isaac/dev/loom-arras/.claude/worktrees/v01-study/loom/.venv/bin/loom
cd "$Q" || exit 1
export AI_AGENT=1
run() {
  for i in 1 2 3; do
    s=$(python3 -c 'import time; print(time.time())')
    "$L" "$@" > /dev/null 2>&1; rc=$?
    e=$(python3 -c 'import time; print(time.time())')
    python3 -c "print(f'{$e-$s:6.2f}  rc=$rc  loom $*')"
  done
}
echo "load $(sysctl -n vm.loadavg)"
run --version
run status
run status --json
run search localization
run source "$2"
run source drafting/draft5.tex
run changes
run ai orient
run lint
run deps "$2"
run ai annotations
echo "load $(sysctl -n vm.loadavg)"
