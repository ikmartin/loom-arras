// Static deployment (book 10.7): build the SPA, then write an index.html for every route the manifest names so pretty URLs work on any static host, and copy the build directory beside them. The pages are the SPA shell; content still loads from build/manifest.json in the browser (server-rendered content is a later step, recorded in docs/deviations.md).
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { join } from 'node:path';

const [buildDir = 'tests/fixture', outDir = 'site'] = process.argv.slice(2);
// the app's own prefix, matching the bundle it was built for; the routes below are written under it
const base = (process.env.ARRAS_BASE ?? '').replace(/\/+$/, '');
if (!existsSync(join(buildDir, 'manifest.json'))) {
	console.error(`${buildDir} has no manifest.json`);
	process.exit(2);
}
execSync('node scripts/stage-fixture.mjs ' + buildDir, { stdio: 'inherit' });
execSync('npx vite build', { stdio: 'inherit' });
execSync('node scripts/stage-fixture.mjs --clean', { stdio: 'inherit' });
const manifest = JSON.parse(readFileSync(join(buildDir, 'manifest.json'), 'utf8'));
const enc = (s) => s.split('/').map(encodeURIComponent).join('/');
const stem = (p) => p.split('/').pop().replace(/\.tex$/, '');
const routes = new Set(['/', '/review', '/problems', '/blockers', '/graph', '/threads', '/tags', '/taxa', '/library', '/loose']);
for (const key of Object.keys(manifest.nodes ?? {})) routes.add('/node/' + enc(key));
for (const m of manifest.masters ?? []) routes.add('/master/' + encodeURIComponent(stem(m.path)));
for (const c of manifest.canon ?? []) routes.add('/canon/' + encodeURIComponent(c.stem));
for (const ck of Object.keys(manifest.references ?? {})) routes.add('/library/' + encodeURIComponent(ck));
for (const t of Object.keys(manifest.tags ?? {})) routes.add('/tag/' + encodeURIComponent(t));
for (const t of Object.values(manifest.taxa ?? {})) routes.add('/taxon/' + encodeURIComponent(t.slug));
for (const s of manifest.sessions ?? []) routes.add('/session/' + encodeURIComponent(s.id));
rmSync(outDir, { recursive: true, force: true });
// With a base, the whole site lives under it: the assets the shell names are `<base>/_app/...`, so the built files
// and the prerendered routes have to sit in the same place or every asset 404s. The directory is then served at the
// origin root and the app answers under its prefix.
const siteRoot = base ? join(outDir, base.slice(1)) : outDir;
cpSync('build', siteRoot, { recursive: true });
const shell = readFileSync(join('build', 'index.html'), 'utf8');
for (const route of routes) {
	if (route === '/') continue;
	const dir = join(siteRoot, decodeURIComponent(route));
	mkdirSync(dir, { recursive: true });
	writeFileSync(join(dir, 'index.html'), shell);
}
writeFileSync(join(outDir, 'routes.json'), JSON.stringify([...routes].map((r) => base + r).sort(), null, 1));
console.log(`prerendered ${routes.size} routes into ${outDir}/`);
