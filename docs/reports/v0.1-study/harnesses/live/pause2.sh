#!/bin/zsh -f
. /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/env.sh
kill $(cat /private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/serve-agent.pid); sleep 3
/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/hcmd.sh '[["wait","3000"],["eval","document.body.innerText.slice(0,300)"],["eval","document.body.innerText.match(/(lost|disconnect|not running|stopped|offline|reconnect)[^\\n]{0,120}/gi)"],["shot","/private/tmp/claude-501/-Users-isaac-dev-loom-arras/f0ec29b5-fd45-4e3f-ae50-d9f9d632cd2f/scratchpad/study/live/shots/09b-viewer-after-serve-stopped.png"]]'
