#!/bin/sh
# Run a command with nothing outside the current tree, TeX Live, and poppler visible: empty HOME and TEXMF trees, no user config, no shell environment.
# Usage: demos/hermetic.sh loom init demos/man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man --no-git --yes
# The quilts under demos/ built from real papers are made this way so that a compile can only read files inside the fixture directory (a macro defined somewhere else on the machine cannot make a test pass).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
LOOM_BIN=${LOOM_BIN:-$HERE/../loom/.venv/bin}
TEXBIN=$(dirname "$(command -v latexmk)")
POPPLER=$(dirname "$(command -v pdftotext)")
EMPTY=$(mktemp -d)
trap 'rm -rf "$EMPTY"' EXIT
env -i PATH="$LOOM_BIN:$TEXBIN:$POPPLER:/usr/bin:/bin" HOME="$EMPTY" XDG_CONFIG_HOME="$EMPTY/config" TEXMFHOME="$EMPTY/texmf" TEXMFLOCAL="$EMPTY/texmf-local" TEXMFVAR="$EMPTY/var" TEXMFCONFIG="$EMPTY/texmfcfg" "$@"
