#!/bin/bash
# usage: timebuild.sh ENVSCRIPT QUILTDIR LABEL DOC...   compiles each DOC with --html, then loom build; prints seconds per step
. "$1"; Q=$2; LABEL=$3; shift 3
cd "$Q" || exit 1
echo "$LABEL load: $(sysctl -n vm.loadavg)  latexmk=$(which latexmk) make4ht=$(which make4ht)"
t0=$(python3 -I -c 'import time; print(time.time())')
for d in "$@"; do
  s=$(python3 -I -c 'import time; print(time.time())')
  $LOOM compile "$d" --html --json > "$S/logs/$LABEL-$(basename $d .tex).json" 2>/dev/null
  e=$(python3 -I -c 'import time; print(time.time())')
  printf "%s compile+html %s: %.1fs\n" "$LABEL" "$d" "$(echo "$e - $s" | bc)"
done
s=$(python3 -I -c 'import time; print(time.time())')
$LOOM build --json > "$S/logs/$LABEL-build.json" 2>/dev/null
e=$(python3 -I -c 'import time; print(time.time())')
printf "%s build: %.1fs\n" "$LABEL" "$(echo "$e - $s" | bc)"
printf "%s total: %.1fs  load after: %s\n" "$LABEL" "$(echo "$e - $t0" | bc)" "$(sysctl -n vm.loadavg)"
