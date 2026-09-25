// A kind's internal views (plan 0.13.3): several readings of one thing, drawn in the rail's cluster rather than in a band the renderer draws for itself.

import type { Manifest } from '$lib/manifest/types';

export interface View {
	id: string;
	label: string;
}

/** A work's views, paper first (K1): the digest only where there is one, or a proposal to judge. */
export function workViews(m: Manifest, citekey: string): View[] {
	const ref = m.references[citekey];
	const proposals = (ref?.proposed?.nodes ?? []).some((id) => !!ref?.results?.[id]);
	return [{ id: 'paper', label: 'Paper' }, ...(ref?.digest || proposals ? [{ id: 'digest', label: 'Digest' }] : []), { id: 'info', label: 'Info' }];
}
