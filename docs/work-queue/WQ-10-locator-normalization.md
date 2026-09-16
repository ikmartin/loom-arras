# WQ-10 · Locator normalization beyond English

**Repo:** loom

## Trigger

A digest whose locators do not match its citations — `loom:unmatched-postnote` firing on a reference paper in another language.

## Why deferred

Results numbered by letters (`Theorem A` → `thm-A.20`) and by Roman numerals already match through the lowercase normalization of §8.7.1, and no fixture has produced a miss. The matcher is a table; the table grows when something falls out of it.

## Rough design

Extend the locator table with the abbreviations used in French, German, Italian and Russian mathematical writing (*Satz*, *Lemme*, *Proposizione*, and so on), mapping to the same display names the English abbreviations map to. A table entry, not a mechanism.

## Blast radius

`loom/src/loom/digest/` locator matching, Chapter 8 §8.7, one digest fixture in the new language.

## Related

Chapter 8 §8.7; `loom:unmatched-postnote` (DR-66).
