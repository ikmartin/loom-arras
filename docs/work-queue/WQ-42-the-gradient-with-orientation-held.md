# WQ-42 · Measure the gradient with orientation held fixed

**Repo:** loom (study, not code)

## Trigger

Before the reference layer is described as making later questions cheaper anywhere a reader outside the project will see it, for instance in a release note (WQ-19).

## Why deferred

Plan 0.12's §13 claims each question in an area is cheaper than the last. The study could not show it: every early/late pair changed the agent's orientation and the corpus at once, and the one pair designed to hold orientation fixed (iteration 4's first and third runs) was not run when the study was stopped. The only clean evidence is one question answered through links in 12 calls against 46 from the papers.

## Rough design

One iteration of §15's loop on a fresh study quilt: an `ai start` run asks the survey question cold; the author verifies what it proposes; a second `ai start` run, reattached, asks the same question. Report calls, time and tokens for both, with `run.log`'s page reads.

## Blast radius

None in code; a row in the report's Table 1.
