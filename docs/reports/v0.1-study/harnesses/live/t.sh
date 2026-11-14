#!/bin/zsh -f
# usage: t.sh LOGFILE cmd...   -- runs cmd with stdin from /dev/null, logs command, wall time, exit and output
log=$1; shift
start=$(python3 -c 'import time;print(time.time())')
out=$("$@" </dev/null 2>&1); rc=$?
end=$(python3 -c 'import time;print(time.time())')
dt=$(python3 -c "print(round($end-$start,2))")
{ print -r -- "\$ $*   [cwd ${PWD/#$S/\$S}] [${dt}s exit $rc]"; print -r -- "$out"; print; } >> $log
print -r -- "[${dt}s exit $rc]"; print -r -- "$out"
