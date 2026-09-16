#!/bin/sh
# Rebuild the example quilts under demos/ from the loom checkout.
#
# demo and synthetic come from loom itself and are always rebuilt. The three quilts built from real papers -- relloc, acgs, man12 -- need tests/fixtures/, whose paper sources are uncommitted (book 14.3), so they are skipped with a message when it is absent, the way the paper test tier skips without LOOM_PAPER_FIXTURES.
#
# These commands are the record of how those quilts were made. They were performed by hand at M4 and M5 and their output is in docs/work-queue/closed/M4.md and M5.md; they live here so that the record is something you can run rather than something you have to transcribe.
set -e
cd "$(dirname "$0")"
if ! command -v loom >/dev/null 2>&1 && ! [ -x ../loom/.venv/bin/loom ]; then
  echo "loom is not installed; run this from a checkout with loom/.venv present" >&2
  exit 2
fi
LOOM=${LOOM:-../loom/.venv/bin/loom}
HERMETIC="sh $(pwd)/hermetic.sh"

rm -rf demo && "$LOOM" init demo --demo --yes
rm -rf synthetic && cp -R ../loom/tests/quilts/synthetic synthetic
echo "refreshed demos/demo and demos/synthetic"

FIX=${LOOM_FIXTURES:-../tests/fixtures}   # overridable so the skip path can be exercised without moving the sources
if ! [ -d "$FIX" ]; then
  echo "tests/fixtures/ is absent (the paper sources are uncommitted): skipping relloc, acgs and man12" >&2
  exit 0
fi

# Every compile below runs through hermetic.sh, so a quilt can only ever read files inside its own tree.
# --fix-anchoring is needed by all three: each paper has theorem-like environments whose \begin or \end
# shares a line with body text, which loom rewrites in its own copy and never in the author's (DR-40).
cd ..
rm -rf demos/relloc
$HERMETIC loom init demos/relloc --from tests/fixtures/relloc/draft3.tex --prefix rl --yes --fix-anchoring
$HERMETIC loom digest extract manolache_VirtualPullbacks2012 tests/fixtures/0805.2065/virtual6.tex --quilt demos/relloc
$HERMETIC loom atomize drafts/draft3.tex drafts/draft4.tex --sections --quilt demos/relloc

rm -rf demos/acgs
$HERMETIC loom init demos/acgs --from tests/fixtures/1709.09864/decomposition-formula.tex --prefix acgs --yes --fix-anchoring
$HERMETIC loom atomize drafts/decomposition-formula.tex drafts/decomposition-formula-atomized.tex --quilt demos/acgs

rm -rf demos/man12
$HERMETIC loom init demos/man12 --from tests/fixtures/0805.2065/virtual6.tex --prefix man --yes --fix-anchoring
$HERMETIC loom atomize drafts/virtual6.tex drafts/virtual6-atomized.tex --sections --quilt demos/man12

echo "refreshed demos/relloc, demos/acgs and demos/man12"
