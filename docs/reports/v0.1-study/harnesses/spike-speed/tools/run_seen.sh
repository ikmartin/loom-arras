#!/bin/bash
# Start serveprobe on the scratch relloc with the scratch clone, run seen.cjs (5 edits to a word in a proof), stop the server.
# Usage: run_seen.sh LABEL PORT [extra serveprobe flags, e.g. --cache-git]
SP=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/spike-speed
LABEL=$1; PORT=$2; shift 2
export XDG_CONFIG_HOME=$SP/xdg
PY=$SP/${CODE:-repo}/loom/.venv/bin/python
Q=$SP/relloc
LOG=$SP/logs/$LABEL-serve.jsonl
rm -f $LOG $LOG.procs.json $Q/.loom/serve.json
echo "$(sysctl -n vm.loadavg)" > $SP/logs/$LABEL.load
$PY $SP/tools/serveprobe.py $Q $PORT $LOG "$@" > $SP/logs/$LABEL-serve.out 2>&1 &
SPID=$!
echo $SPID > $SP/logs/$LABEL.pid
for i in $(seq 1 100); do grep -q listening $LOG 2>/dev/null && break; sleep 0.2; done
UNIQUE=1 TRIALS=${TRIALS:-5} node $SP/tools/seen.cjs http://127.0.0.1:$PORT /master/drafting/draft5 "fixed stack" $Q/drafting/draft5.tex "has fibered products, for which" "unused" $LOG $SP/logs/$LABEL-seen.json 2> $SP/logs/$LABEL-seen.err
if [ -n "$WRITES" ]; then $PY $SP/tools/writes.py $Q $PORT rl-000G $SP/${CODE:-repo}/loom/.venv/bin/loom --http-only > $SP/logs/$LABEL-writes.txt 2>&1; fi
kill -TERM $SPID; wait $SPID
if [ -n "$STATUS" ]; then
  cd $Q; for i in 1 2 3; do s=$(python3 -c 'import time; print(time.time())'); AI_AGENT=1 $SP/${CODE:-repo}/loom/.venv/bin/loom status > /dev/null 2>&1; e=$(python3 -c 'import time; print(time.time())'); python3 -c "print(f'status {$e-$s:6.2f}  load $(sysctl -n vm.loadavg)')"; done > $SP/logs/$LABEL-status.txt
fi
echo "$(sysctl -n vm.loadavg)" >> $SP/logs/$LABEL.load
cat $SP/logs/$LABEL-seen.err
