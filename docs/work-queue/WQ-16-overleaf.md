# WQ-16 · The Overleaf procedure

**Repo:** —

## Trigger

Cutting the first tagged release. The procedure's output — Overleaf's TeX Live version and the comparison result — belongs in the release notes.

## Why deferred

It is a manual procedure requiring an Overleaf account, and it is the author's to run. Acceptance criterion 9 and step 7 of §13.6 have been blocked on it since M7.

## Rough design

Per Chapter 14 §14.5, unchanged:

1. `loom init demo --demo`; `loom compile`; record `pdftotext` of the local PDF.
2. Zip the quilt without `build/`, `refs/pdf/` and `refs/src/`; upload to a new Overleaf project; set `drafts/main.tex` as the main document; compile.
3. Download the PDF; compare `pdftotext` with the local one. Equal modulo whitespace is a pass.
4. Record Overleaf's TeX Live version and the result in the release notes.

While there, settle the open question from Chapter 4 §4.6: whether Overleaf honours `% !TEX root` for main-document selection. The README instructs setting the main document in Overleaf's menu regardless, so nothing depends on the answer — but it is free to observe once someone is in the interface. See [[WQ-09]].

## Blast radius

`loom/docs/RELEASE.md`, Chapter 14 §14.5, Chapter 4 §4.6, the release notes.

## Related

[[WQ-09]], [[WQ-19]]; `closed/M7.md` ("Blocked on the user"); Chapter 13 §13.6 step 7.
