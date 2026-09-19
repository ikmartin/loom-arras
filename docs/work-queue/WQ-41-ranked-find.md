# WQ-41 · Ranking for `loom refs find`

**Repo:** loom

## Trigger

An agent reruns `loom refs find` three or more times in one query to narrow a common word. `run.log` records it, since read commands take `--run` (DR-176).

## Why deferred

`refs find` is a substring search over digested statements, grouped per work. On the study quilt "localization" returns about 150 hits, and agents narrowed by rerunning or fell back to `loom search <author>`. Plan 0.12 deferred ranking; four iterations re-measured it as noisy and never as blocking.

## Rough design

Rank by where the words fall (locator and title before body), by level (a main result first), and by whether the author's own keys cite the work.

## Blast radius

`refs/search.py`, `cli/refs.py` (find).
