#!/bin/sh
# Regenerate docs/specs/fixture/ from loom's build of the synthetic quilt (docs/specs/fixture.md §2), then vendor it into loom/tests/fixture and arras/tests/fixture.
# Runs the real TeX toolchain in an isolated environment so nothing outside the quilt and TeX Live can be read. Timestamps are fixed through LOOM_FIXED_TIME.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
WS=$(cd "$HERE/../../.." && pwd)
LOOM="$WS/loom"
SRC="$LOOM/tests/quilts/synthetic"
OUT="$HERE/../fixture"
export LOOM_FIXED_TIME="2026-09-16T00:00:00Z"
TMP=$(mktemp -d)
EMPTY=$(mktemp -d)
cp -R "$SRC" "$TMP/synthetic"
Q="$TMP/synthetic"
TEXBIN=$(dirname "$(command -v latexmk)")
POPPLER=$(dirname "$(command -v pdftotext)")
run() { env -i PATH="$TEXBIN:$POPPLER:/usr/bin:/bin:$LOOM/.venv/bin" HOME="$EMPTY" TEXMFHOME="$EMPTY" TEXMFLOCAL="$EMPTY" TEXMFVAR="$EMPTY/var" TEXMFCONFIG="$EMPTY/config" LOOM_FIXED_TIME="$LOOM_FIXED_TIME" "$@"; }
run "$LOOM/.venv/bin/loom" compile drafts/main.tex --quilt "$Q"
run "$LOOM/.venv/bin/loom" compile drafts/talk.tex --quilt "$Q"
run "$LOOM/.venv/bin/loom" build --quilt "$Q" || true   # exit 1 is expected: the synthetic quilt carries three intentional errors
rm -rf "$OUT"
mkdir -p "$OUT"
cp "$Q/build/manifest.json" "$OUT/"
cp -R "$Q/build/fragments" "$OUT/fragments"
[ -d "$Q/build/svg" ] && cp -R "$Q/build/svg" "$OUT/svg"
[ -d "$Q/build/diffs" ] && cp -R "$Q/build/diffs" "$OUT/diffs"
VERSION=$(cd "$LOOM" && .venv/bin/loom --version | awk '{print $2}')
IFACE=$(python3 -c "import json;print(json.load(open('$OUT/manifest.json'))['interface_version'])")
printf 'interface %s\nloom %s\ngenerated %s\n' "$IFACE" "$VERSION" "$LOOM_FIXED_TIME" > "$OUT/VERSION"
for dest in "$LOOM/tests/fixture" "$WS/arras/tests/fixture"; do
  rm -rf "$dest"; mkdir -p "$dest"; cp -R "$OUT"/. "$dest"/
done
python3 "$HERE/validate-dialect.py" "$OUT/fragments"
echo "fixture refreshed: $(find "$OUT/fragments" -name '*.html' | wc -l | tr -d ' ') fragments, interface $IFACE, loom $VERSION"
rm -rf "$TMP" "$EMPTY"
