#!/bin/sh
# Send one command (or a JSON array of commands) to the running driver.
curl -s --max-time 120 -X POST "http://127.0.0.1:${DRIVER_PORT:-48199}/" -d "$1"; echo
