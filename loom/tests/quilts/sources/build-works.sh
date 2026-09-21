#!/bin/sh
# Compile every invented cited work -- `showcase-works/`, `demo-works/` -- to the PDF beside it.
#
# The PDFs are committed, and this script is what makes them. It is not part of generating a quilt: `gen_quilts.py` copies these bytes into the quilt's seed space and lets `loom refs scan` file them, so that generating a quilt needs no TeX distribution and produces the same bytes on every machine. Run this only when one of the `.tex` files changes, and commit the result.
#
# Hermetic, like every other compile in this repository: empty HOME and empty TeX trees, so a macro defined elsewhere on the machine cannot make one of these work. `SOURCE_DATE_EPOCH` and Ghostscript's three `-dOmit…` flags are what make the bytes reproducible -- rerun this on an unchanged `.tex` and git sees nothing. Ghostscript is required rather than optional because it is also what keeps the committed PDFs small, and these quilts commit them.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
command -v latexmk >/dev/null || { echo "latexmk is not on PATH" >&2; exit 1; }
command -v gs >/dev/null || { echo "ghostscript (gs) is not on PATH; it is what makes these PDFs small and reproducible" >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/home" "$work/texmf" "$work/texmf-local" "$work/var" "$work/cfg"

for tex in "$here"/*-works/*.tex; do
  dir=$(dirname "$tex")
  name=$(basename "$tex" .tex)
  cp "$tex" "$work/"
  ( cd "$work" && env -u TEXINPUTS \
      HOME="$work/home" TEXMFHOME="$work/texmf" TEXMFLOCAL="$work/texmf-local" \
      TEXMFVAR="$work/var" TEXMFCONFIG="$work/cfg" \
      SOURCE_DATE_EPOCH=1758240000 FORCE_SOURCE_DATE=1 \
      latexmk -pdf -interaction=nonstopmode -halt-on-error "$name.tex" >/dev/null )
  gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/prepress \
     -dOmitInfoDate=true -dOmitID=true -dOmitXMP=true \
     -sOutputFile="$dir/$name.pdf" "$work/$name.pdf"
  echo "wrote ${dir##*/}/$name.pdf ($(wc -c <"$dir/$name.pdf") bytes)"
done
