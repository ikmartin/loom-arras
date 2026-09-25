import type { Key, Manifest } from '$lib/manifest/types';

/** The review rows owned by one working document, including proofs through their statement owner. */
export function documentKeys(manifest: Manifest, path: string): Key[] {
	return Object.values(manifest.keys).filter((key) => manifest.nodes[key.node]?.reached_by.includes(path));
}
