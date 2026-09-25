// The vocabulary of an annotation, once, for every composer (book 15.3.1, 15.3.10).
//
// Five kinds, each a noun; `note` is the explanation-or-aside kind and asks nothing, so it is every composer's default. Severity grades a fault and only two kinds claim one; a graded question is a category error, and the publisher refuses it.

export const KINDS = ['objection', 'suggestion', 'question', 'citation', 'note'] as const;
export type Kind = (typeof KINDS)[number];

/** The kinds that take a severity. */
export const GRADED: readonly string[] = ['objection', 'suggestion'];

export const SEVERITIES = ['major', 'moderate', 'minor'] as const;

/** What the composer's submit says for each kind: the verb of the thing being done. */
export const VERBS: Record<Kind, string> = { objection: 'Object', suggestion: 'Suggest', question: 'Ask', citation: 'Cite', note: 'Note' };
