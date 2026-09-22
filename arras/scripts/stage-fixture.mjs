// Copy the vendored conformance fixture into static/build so `vite dev` and `vite preview` serve it at /build/, the same place loom serve publishes. `--clean` removes it so a production build ships no fixture.
import { cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const arg = process.argv[2] ?? 'tests/fixture';
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
rmSync('static/build', { recursive: true, force: true });
rmSync('static/digests', { recursive: true, force: true });
cpSync(arg, 'static/build', { recursive: true });

// `artifacts.dir` is quilt-relative and sits beside `build/`, not inside it, which is what `artifactUrl` climbs out
// for. A preview server that serves only the build directory therefore cannot serve the papers, and the viewer renders
// them itself now rather than handing a URL to an iframe — so a staged corpus with no store has no paper to draw.
const store = resolve(dirname(resolve(arg)), 'digests', 'storage');
if (existsSync(store)) {
	cpSync(store, join('static', 'digests', 'storage'), { recursive: true });
	console.log('staged the store beside it, so the papers are servable');
}
console.log(`staged ${arg} -> static/build`);
