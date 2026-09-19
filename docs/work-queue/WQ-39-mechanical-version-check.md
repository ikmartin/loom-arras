# WQ-39 · A mechanical version check for extracted digests

**Repo:** loom

## Trigger

The author cites, with a locator, a result in a digest `loom:unverified-locators` flags, and the cited version numbers it differently.

## Why deferred

DR-181 restored the warning that a digest's numbers are another version's; nothing checks them. Chang–Kiem–Li's preprint numbers its main theorem 3.4 and the published paper 3.5, because the published version gained a remark, and the conclusion differs. An agent found it by reading the PDF page by page. A check could have found it without one. It is not built because it is a new check with its own false positives (a text layer that mangles "Theorem 3.5"), and the warning now says the numbers are unverified.

## Rough design

For each extracted result of a flagged digest, find its opening words in the cited PDF's committed page text, read the number printed before them, and compare it with the digest's. Report disagreements as a warning naming both numbers. Store the published number as an id-shaped alias when every result agrees on a consistent shift, as DR-75 does for two arXiv versions.

## Blast radius

`refs/search.py` (locating statements), `scan/lint.py`, `digest/extract.py` or a `refs` verb that writes the aliases.
