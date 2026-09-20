// Copy the built SPA into the optional pip wrapper so `pip install ./python` ships the viewer. Loom does not depend on this; it vendors the same build/ with its own script.
import { cpSync, existsSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { execSync } from 'node:child_process';

const src = 'build';
const dest = 'python/src/arras/bundle';
if (!existsSync(`${src}/index.html`)) {
	console.error('build/ has no index.html; run `npm run build` first');
	process.exit(2);
}
rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(src, dest, { recursive: true });
let commit = 'unknown';
try {
	commit = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim();
} catch {}
writeFileSync(`${dest}/VERSION`, `arras ${commit} interface 1\n`);
console.log(`copied ${src} -> ${dest}`);
