// Where each comment on a key stands in a fragment, for the Comments setting (book 15.3.1, plan 0.13 §7).
//
// Shown in place, a comment with a mark is reached from its mark and one without gets a count beside its node's label;
// in the margin column, every comment gets a gutter slot unless it is long, when it stands inline below the node. One
// function for every route, because `margin` chosen on a node page or in the Library View used to disable the in-place
// controller and build no gutter either -- the annotations there could only be opened from the list below.

import type { Annotation, Manifest } from '$lib/manifest/types';
import type { CommentSlot } from './mount';
import { openOn, repliesTo } from '$lib/annotations';
import { prefs } from '$lib/prefs.svelte';

/** How much a comment may say before a gutter is the wrong place for it. Measured on the rendered text of the comment and its replies. */
export const GUTTER_LIMIT = 220;

/** The rendered length of a comment and its replies, which is what decides whether it fits a gutter. */
export function plainLength(m: Manifest, a: Annotation): number {
	const own = a.body_html.replace(/<[^>]*>/g, '').trim().length + (a.quote?.length ?? 0);
	return own + repliesTo(m, a.id).reduce((n, r) => n + r.body_html.replace(/<[^>]*>/g, '').trim().length, 0);
}

/** The undiscarded top-level comments on exactly this key, in manifest order. A proof has an element of its own, so matching a node's proofs here as well would place the same comment twice. */
export function commentsOn(m: Manifest, key: string): Annotation[] {
	return openOn(m, key);
}

/** The slot function a `Fragment` takes, reading the placement setting live. */
export function slotsFor(m: () => Manifest): (key: string) => CommentSlot[] {
	return (key) => {
		const manifest = m();
		if (prefs.comments !== 'margin') {
			return commentsOn(manifest, key)
				.filter((a) => !(a.anchored && a.quote))
				.map((a) => ({ id: a.id, where: 'count' }));
		}
		return commentsOn(manifest, key).map((a) => ({ id: a.id, where: plainLength(manifest, a) > GUTTER_LIMIT ? 'inline' : 'gutter' }));
	};
}
