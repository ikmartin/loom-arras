# Mode: question

## Before you begin
- Write only under your session's directory. Never edit source. Never run `loom accept`.
- Read `ai/rules.md` once this session.

## Purpose
Answer a question about a key or about the quilt, thoroughly, with the five blocks of the output contract under a [summary].

## Input
The closure of the key concerned, or `loom status --json` for quilt-level questions; anything further through loom commands.

## Output
1. `question-SLUG.notes.md`: [summary], [definition], [worked-examples], [edge-cases], [stress-test], [answer].
2. Annotations only if the question revealed a defect in a key (then as audit would record it).
3. A message in the chat (`loom session say`) saying what you did and what remains.

## Checklist
- [ ] Every claim carries an epistemic label.
- [ ] Trials are saved and reported.
- [ ] Nothing was written outside your session's directory.
