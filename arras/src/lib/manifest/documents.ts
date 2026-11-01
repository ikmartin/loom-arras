// What a document is, read from its manifest entry.

import type { Master } from './types';

/** Whether a document is an agent's: a copy of one of the person's documents, `copy_of` naming it, as the history records it (docs/specs/manifest.md §2a). */
export function isAgentDocument(m: Pick<Master, 'copy_of'> | null | undefined): boolean {
	return !!m?.copy_of;
}
