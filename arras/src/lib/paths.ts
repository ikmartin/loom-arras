// Where the app lives and where the corpus lives (plan 0.9.5 R1). Two different things, and a host may move either.
//
// `base` is SvelteKit's: the prefix the app's own routes are served under, fixed when the bundle is built.
// The data root is the build directory the publisher wrote — `manifest.json` and the fragments beside it. It defaults
// to `build/` next to the app, which is where a publisher serving both puts it, and a host may point it anywhere
// before the app boots: a different path, a different origin, a corpus that is not beside the viewer at all.
// Nothing in `src/lib/` builds an origin-absolute URL by hand; every one comes from here.

import { base } from '$app/paths';

let root = '';

function normalise(url: string): string {
	return url.replace(/\/+$/, '') + '/';
}

/** The corpus's build directory, with a trailing slash. */
export function dataRoot(): string {
	return root || normalise(base + '/build');
}

/**
 * Point the viewer at a corpus. A host calls this once, before the app boots; passing an empty string restores the
 * default. Accepts a path (`/papers/build`) or an absolute URL (`https://example.org/corpus/build`).
 */
export function setDataRoot(url: string): void {
	root = url ? normalise(url) : '';
}

/** A file inside the corpus's build directory, by its manifest-relative path. */
export function dataUrl(path: string): string {
	return dataRoot() + path.replace(/^\/+/, '');
}

/** A file the publisher serves beside the build directory, such as a fetched paper under `refs/`. */
export function artifactUrl(dir: string): string {
	return dataRoot().replace(/build\/$/, '') + dir.replace(/^\/+|\/+$/g, '') + '/paper.pdf';
}

/** A route of this app, prefixed by the base path the bundle was built for. */
export function route(path: string): string {
	return base + path;
}
