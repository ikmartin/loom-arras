// Where each comment on a key stands in a fragment (book 15.3.1).
//
// A comment with a mark is reached from its mark; one without gets a count beside its node's label. The `margin`
// placement, which sorted comments between a gutter slot and the flow by how much they said, is retired.

import type { Annotation, Manifest } from '$lib/manifest/types';
import type { CommentSlot } from './mount';
import { openOn } from '$lib/annotations';

/** The undiscarded top-level comments on exactly this key, in manifest order. A proof has an element of its own, so matching a node's proofs here as well would place the same comment twice. */
export function commentsOn(m: Manifest, key: string): Annotation[] {
	return openOn(m, key);
}

/**
 * The slot function a `Fragment` takes.
 *
 * A comment with a mark is reached from its mark; one without gets a count beside its node's label. The `margin`
 * placement, which put short comments in the gutter and long ones in the flow, is retired.
 */
export function slotsFor(m: () => Manifest): (key: string) => CommentSlot[] {
	return (key) =>
		commentsOn(m(), key)
			.filter((a) => !(a.anchored && a.quote))
			.map((a) => ({ id: a.id, where: 'count' }));
}
