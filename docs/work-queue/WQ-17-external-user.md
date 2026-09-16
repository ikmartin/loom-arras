# WQ-17 · Acceptance criterion 10: an external user

**Repo:** —

## Trigger

Someone outside the project has a paper they want to bring in.

## Why deferred

It needs a second person, which no amount of implementation supplies. Blocked since M7.

## Rough design

A second person runs `loom init --from` on their own paper, following `README.md` alone, and reaches `loom status`. **Anything they had to ask is a README bug**, and that is the entire measurement — the deliverable is the list of questions, not a pass or a fail.

Criterion 10 gates the claim "MVP done", not the first tagged release, so [[WQ-19]] does not wait on it.

## Blast radius

`loom/README.md` and `arras/README.md`, Chapter 2's success criteria, Chapter 13 §13.6 step 7.

## Related

[[WQ-16]], [[WQ-19]]; `closed/M7.md`; Chapter 2.
