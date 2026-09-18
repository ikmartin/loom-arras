// Fragments are fetched lazily and cached per manifest hash; a new manifest drops the cache.
import { dataUrl } from '$lib/paths';

const cache = new Map<string, Promise<string>>();
let cacheHash = '';

export function fetchFragment(path: string, hash: string): Promise<string> {
	if (hash !== cacheHash) {
		cache.clear();
		cacheHash = hash;
	}
	const key = path;
	let p = cache.get(key);
	if (!p) {
		p = fetch(dataUrl(path), { cache: 'no-cache' }).then((r) => {
			if (!r.ok) throw new Error(`${path}: ${r.status}`);
			return r.text();
		});
		cache.set(key, p);
	}
	return p;
}
