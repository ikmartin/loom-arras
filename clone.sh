#!/bin/sh
# Clone the two tool repositories beside this script. Safe to re-run: existing clones are left alone.
set -e
cd "$(dirname "$0")"
[ -d loom/.git ]  || git clone https://github.com/ikmartin/loom.git loom
[ -d arras/.git ] || git clone https://github.com/ikmartin/arras.git arras
echo "loom and arras are cloned. Next: see loom/README.md and arras/README.md."
