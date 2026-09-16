#!/bin/sh
# Regenerate demos/demo and demos/synthetic from the loom checkout. Completed at M1; until then this only explains itself.
set -e
cd "$(dirname "$0")"
if ! command -v loom >/dev/null 2>&1 && ! [ -x ../loom/.venv/bin/loom ]; then
  echo "loom is not installed yet (M0). Run this after M1." >&2
  exit 2
fi
LOOM=${LOOM:-../loom/.venv/bin/loom}
rm -rf demo && "$LOOM" init demo --demo --yes
rm -rf synthetic && cp -R ../loom/tests/quilts/synthetic synthetic
echo "refreshed demos/demo and demos/synthetic"
