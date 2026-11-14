#!/bin/zsh -f
# Logs what the client hands loom's MCP server (argv, cwd, env, stdin) and when it starts and exits, then runs the real server.
zmodload zsh/datetime
L=/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/presence/${EPOCHREALTIME%.*}-$$
mkdir -p $L
{ print "start $EPOCHREALTIME"; print -r -- "argv $*"; print "cwd $PWD"; print "ppid $PPID $(ps -o comm= -p $PPID)"; env | grep -E '^(PATH|CLAUDE|AI_AGENT|HOME|USER|LANG|TERM|MCP|CODEX|XDG|TMPDIR)' | grep -v TOKEN } > $L/meta
trap 'print "signal TERM $EPOCHREALTIME" >> $L/meta' TERM; trap 'print "signal HUP $EPOCHREALTIME" >> $L/meta' HUP; trap 'print "signal INT $EPOCHREALTIME" >> $L/meta' INT
tee $L/stdin.jsonl | ${LOOM_REAL:-/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/uv/tools/loomtex/bin/loom} "$@" | tee $L/stdout.jsonl
print "exit $EPOCHREALTIME status $pipestatus" >> $L/meta
