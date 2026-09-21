// The vocabulary of an annotation, once, for every composer (plan 0.13 §7).
//
// Six kinds. `confirmation` replaced `ok`: every other kind is a noun, and `good` would be praise where the claim is
// that something checks out. `note` is the explanation-or-aside kind, and asks nothing. Severity grades a fault, and
// only two kinds claim one; a graded question is a category error, and the publisher refuses it.

export const KINDS = ['objection', 'suggestion', 'question', 'confirmation', 'citation', 'note'] as const;
export type Kind = (typeof KINDS)[number];

/** The kinds that take a severity. */
export const GRADED: readonly string[] = ['objection', 'suggestion'];

export const SEVERITIES = ['', 'major', 'moderate', 'minor'] as const;
