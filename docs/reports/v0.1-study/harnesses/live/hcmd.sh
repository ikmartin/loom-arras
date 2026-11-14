#!/bin/zsh -f
# hcmd.sh 'JSON steps' -> runs in the holder and prints its output
D=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/holder
n=1; while [[ -e $D/cmd-$n.json ]]; do n=$((n+1)); done
print -r -- "$1" > $D/cmd-$n.json.tmp && mv $D/cmd-$n.json.tmp $D/cmd-$n.json
for i in {1..240}; do [[ -e $D/out-$n.txt ]] && { cat $D/out-$n.txt; exit 0 }; sleep 0.5; done
echo "holder timeout"
