// Copy the vendored conformance fixture into static/build so `vite dev` and `vite preview` serve it at /build/, the same place loom serve publishes. `--clean` removes it so a production build ships no fixture.
import { cpSync, existsSync, rmSync } from 'node:fs';

const arg = process.argv[2] ?? 'tests/fixture';
if (arg === '--clean') {
	rmSync('static/build', { recursive: true, force: true });
	console.log('removed static/build');
	process.exit(0);
}
if (!existsSync(`${arg}/manifest.json`)) {
	console.error(`${arg} has no manifest.json`);
	process.exit(2);
}
rmSync('static/build', { recursive: true, force: true });
cpSync(arg, 'static/build', { recursive: true });
console.log(`staged ${arg} -> static/build`);
