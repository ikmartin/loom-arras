// Which keys name a document rather than a node (plan 0.11 Parts B and C). Model facts in, display facts out: nothing here touches the DOM.

import type { Manifest } from '$lib/manifest/types';

/** Whether a key names a document rather than a node: a master or a canon document, both keyed by path. An annotation's target may be a path as easily as a key. */
export function isDocument(m: Manifest, key: string): boolean {
	return m.masters.some((x) => x.path === key) || !!m.canon?.some((c) => c.path === key);
}
