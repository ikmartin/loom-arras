// Copy a corpus build directory (default the vendored conformance fixture) to `INTO/build`, where the app looks for it and loom serve publishes it. INTO defaults to `static`, so `vite dev` serves it; the Playwright configs stage into their own copy of the built app instead (scripts/bundle.mjs). `--clean` removes it from `static` so a production build ships no fixture.
//
// Usage: node scripts/stage-fixture.mjs [FIXTURE [INTO]] | --clean
import { cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const arg = process.argv[2] ?? 'tests/fixture';
const into = process.argv[3] ?? 'static';
if (arg === '--clean') {
	rmSync('static/build', { recursive: true, force: true });
	rmSync('static/digests', { recursive: true, force: true });
	console.log('removed static/build');
	process.exit(0);
}
if (!existsSync(`${arg}/manifest.json`)) {
	console.error(`${arg} has no manifest.json`);
	process.exit(2);
}
rmSync(join(into, 'build'), { recursive: true, force: true });
rmSync(join(into, 'digests'), { recursive: true, force: true });
cpSync(arg, join(into, 'build'), { recursive: true });

// `artifacts.dir` is quilt-relative and sits beside `build/`, not inside it, which is what `artifactUrl` climbs out for. A server that serves only the build directory therefore cannot serve the papers, and the viewer renders them itself rather than handing a URL to an iframe, so a staged corpus with no store has no paper to draw.
const store = resolve(dirname(resolve(arg)), 'digests', 'storage');
if (existsSync(store)) {
	cpSync(store, join(into, 'digests', 'storage'), { recursive: true });
	console.log('staged the store beside it, so the papers are servable');
}
console.log(`staged ${arg} -> ${join(into, 'build')}`);
