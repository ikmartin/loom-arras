// Where each annotation on a key stands in a fragment (book 15.3.1).
//
// An annotation with a mark is reached from its mark; one without -- no quote, or an anchor that no longer resolves -- is a mark on its node's label. One that names the document it is read in is marked there and nowhere else.

import type { Annotation, Manifest } from '$lib/manifest/types';
import { settled, type CommentSlot } from './mount';
import { on } from '$lib/annotations';
import { ui } from '$lib/ui.svelte';

/** The top-level annotations on exactly this key, in manifest order, settled ones included: a discarded annotation is settled like a resolved one, hidden at rest and drawn faintly by the settled control (15.3.1). A proof has an element of its own, so matching a node's proofs here as well would place the same annotation twice. */
export function commentsOn(m: Manifest, key: string): Annotation[] {
	return on(m, key);
}

/**
 * The slot function a `Fragment` takes: every annotation on the key that has no mark of its own goes on the label.
 *
 * `master` is the document the fragment is read in, when it is one; an annotation that names a document is placed only in that document, and never on a node's own page. A settled one gets a label mark only while settled annotations are shown, since at rest it would be nothing to see and nothing to click.
 */
export function slotsFor(m: () => Manifest, master: () => string | null = () => null): (key: string) => CommentSlot[] {
	return (key) =>
		commentsOn(m(), key)
			.filter((a) => !(a.anchored && a.quote))
			.filter((a) => !a.in || a.in === master())
			.filter((a) => !settled(a) || ui.showSettled)
			.map((a) => ({ id: a.id, where: 'label' }));
}
