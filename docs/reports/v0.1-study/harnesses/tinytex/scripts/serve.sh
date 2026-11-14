#!/bin/bash
# usage: serve.sh ENVSCRIPT QUILT PORT LOG ; starts loom serve in the background, prints its pid
. "$1"; cd "$2" || exit 1
nohup $LOOM serve --port "$3" > "$4" 2>&1 &
echo $!
