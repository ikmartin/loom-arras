#!/bin/sh
# Compile the showcase's invented cited works to the PDFs beside them.
#
# The PDFs are committed, and this script is what makes them. It is not part of generating the quilt: `gen_quilts.py showcase` copies these bytes into the quilt's seed space and lets `loom refs scan` file them, so that generating the demo needs no TeX distribution and produces the same bytes on every machine. Run this only when one of the `.tex` files here changes, and commit the result.
#
# Hermetic, like every other compile in this repository: empty HOME and empty TeX trees, so a macro defined elsewhere on the machine cannot make one of these work. `SOURCE_DATE_EPOCH` and Ghostscript's three `-dOmit…` flags are what make the bytes reproducible -- rerun this on an unchanged `.tex` and git sees nothing. Ghostscript is required rather than optional because it is also what keeps the committed PDFs to a third of latexmk's size, and the showcase commits them.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
command -v latexmk >/dev/null || { echo "latexmk is not on PATH" >&2; exit 1; }
command -v gs >/dev/null || { echo "ghostscript (gs) is not on PATH; it is what makes these PDFs small and reproducible" >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/home" "$work/texmf" "$work/texmf-local" "$work/var" "$work/cfg"

for tex in "$here"/*.tex; do
  name=$(basename "$tex" .tex)
  cp "$tex" "$work/"
  ( cd "$work" && env -u TEXINPUTS \
      HOME="$work/home" TEXMFHOME="$work/texmf" TEXMFLOCAL="$work/texmf-local" \
      TEXMFVAR="$work/var" TEXMFCONFIG="$work/cfg" \
      SOURCE_DATE_EPOCH=1758240000 FORCE_SOURCE_DATE=1 \
      latexmk -pdf -interaction=nonstopmode -halt-on-error "$name.tex" >/dev/null )
  gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress \
     -dOmitInfoDate=true -dOmitID=true -dOmitXMP=true \
     -sOutputFile="$here/$name.pdf" "$work/$name.pdf"
  echo "wrote $name.pdf ($(wc -c <"$here/$name.pdf") bytes)"
done
