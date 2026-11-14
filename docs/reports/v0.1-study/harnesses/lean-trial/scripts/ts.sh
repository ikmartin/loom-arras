#!/bin/bash
# usage: ts.sh LOGFILE -- command args...  ; prefixes each output line with a timestamp, records rx bytes on en0 before/after
log="$1"; shift; shift
rx() { netstat -ib | awk '/en0/ && /Link/ {print $7; exit}'; }
echo "START $(date +%T) rx=$(rx) df=$(df -k /System/Volumes/Data | awk 'NR==2{print $4}')" > "$log"
start=$(date +%s)
"$@" 2>&1 | while IFS= read -r line; do echo "$(date +%T) $line"; done >> "$log"
rc=${PIPESTATUS[0]}
echo "END $(date +%T) rc=$rc elapsed=$(( $(date +%s) - start ))s rx=$(rx) df=$(df -k /System/Volumes/Data | awk 'NR==2{print $4}')" >> "$log"
