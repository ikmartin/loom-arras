#!/bin/zsh -f
. /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/env.sh
uv tool install --force /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/loom-v2 2>&1 | tail -3
/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/uv/bin/loom --version
sleep 8
/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/hcmd.sh '[["eval","document.body.innerText.match(/restart[^\\n]{0,160}|out of step[^\\n]{0,160}|newer[^\\n]{0,160}/gi)"],["shot","/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/shots/09a-viewer-after-loom-replaced.png"]]'
tail -5 /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/logs/serve-agent.log
