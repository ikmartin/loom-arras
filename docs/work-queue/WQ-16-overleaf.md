# WQ-16 · The Overleaf procedure

**Repo:** —

## Trigger

Cutting the first tagged release. The procedure's output — Overleaf's TeX Live version and the comparison result — belongs in the release notes.

## Why deferred

It is a manual procedure requiring an Overleaf account, and it is the author's to run. Acceptance criterion 9 and step 7 of §13.6 have been blocked on it since M7.

## Rough design

Unchanged:

1. `loom init demo --demo`; `loom compile drafting/main.tex`; record `pdftotext` of the local PDF (`.loom/build/drafting/main/main.pdf`).
2. Send the document to a new Overleaf project the way a person does: clone the project, pair with `loom sync init DIR`, and `loom sync publish --push`. A document compiles from its own directory with loom's macros inline (plan 0.22.4), so the project holds that directory alone, its main `main.tex` at the top; compile it on Overleaf.
3. Download the PDF; compare `pdftotext` with the local one. Equal modulo whitespace is a pass.
4. Record Overleaf's TeX Live version and the result in the release notes.

While there, settle the open question whether Overleaf honours `% !TEX root` for main-document selection. The README instructs setting the main document in Overleaf's menu regardless, so nothing depends on the answer — but it is free to observe once someone is in the interface. Recording it for loose files was WQ-09, since closed.

## Blast radius

`loom/docs/RELEASE.md`, the release notes.

## Related

[[WQ-19]]; `closed/M7.md` ("Blocked on the user").6 step 7.
