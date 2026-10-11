// Global setup for the live perf suite: the app once, and one prepared copy of `PERF_QUILT` that every test's server copies again (served.ts).
//
// The copy is seeded the way a working session leaves a quilt: a session, forty quote-anchored annotations of every kind with replies and resolutions, and the main document's compiled PDF filed for one work, so the PDF views have a document. Loom runs as the author, as served.ts runs it.

import type { FullConfig } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, readFileSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { ARRAS, LOOM, reviewerEnv, scratchDir, suiteOf } from '../served';

interface ManifestNode {
	kind?: string;
	file?: string;
	reached_by?: string[];
}

interface Manifest {
	nodes: Record<string, ManifestNode>;
	masters: { path: string; default?: boolean; pdf?: string }[];
	references: Record<string, unknown>;
}

const KINDS = ['objection', 'suggestion', 'question', 'note'];
const SEVERITIES = ['major', 'moderate', 'minor'];

/** Four-word phrases that occur once in `text`, for quotes that anchor to one place. */
export function phrases(text: string): string[] {
	const found = text.match(/(?<![\\$\w])[A-Za-z]{4,}(?: [A-Za-z]{2,}){3}(?![\w$])/g) ?? [];
	return found.filter((p) => text.split(p).length === 2);
}

/** The default master of a built quilt, and every node it reaches whose own file is in the author's text. */
export function reading(root: string): { master: Manifest['masters'][number]; nodes: [string, ManifestNode][] } {
	const m = JSON.parse(readFileSync(join(root, 'build', 'manifest.json'), 'utf8')) as Manifest;
	const master = m.masters.find((x) => x.default) ?? m.masters[0];
	const nodes = Object.entries(m.nodes).filter(
		([, n]) => n.file && !n.file.startsWith('digests/') && (n.reached_by ?? []).includes(master.path) && ['environment', 'proof', 'section'].includes(n.kind ?? '')
	);
	return { master, nodes };
}

export default function setup(config: FullConfig): void {
	const suite = suiteOf({ config });
	const dir = scratchDir(suite);
	rmSync(dir, { recursive: true, force: true });
	execFileSync(process.execPath, [join(ARRAS, 'scripts', 'bundle.mjs'), join(dir, 'bundle')], { cwd: ARRAS, stdio: 'pipe' });

	const source = resolve(ARRAS, process.env.PERF_QUILT ?? '../demos/relloc');
	if (!existsSync(join(source, 'config.toml'))) throw new Error(`PERF_QUILT names no quilt: ${source}`);
	const root = join(dir, 'template');
	cpSync(source, root, { recursive: true, filter: (p) => !p.endsWith('/.git') });

	const env = reviewerEnv(suite, join(dir, 'config'));
	const loom = (args: string[]): string => {
		try {
			return execFileSync(LOOM, [...args, '--quilt', root], { cwd: ARRAS, env, stdio: 'pipe' }).toString();
		} catch (err) {
			// a quilt's own errors make loom exit 1, which is not a failure here; a refused annotation is skipped
			if ((err as { status?: number }).status === 1) return '';
			throw err;
		}
	};
	loom(['build']);
	loom(['session', 'new', '--name', 'perf', '--as', 'Perf Reader']);

	const { master, nodes } = reading(root);
	const made: string[] = [];
	let n = 0;
	for (const [key, node] of nodes) {
		if (made.length >= 40) break;
		const text = readFileSync(join(root, node.file!), 'utf8');
		const quote = phrases(text)[0];
		if (!quote) continue;
		const kind = KINDS[n % KINDS.length];
		const args = ['annotate', key, `Perf finding ${n}.`, '--quote', quote, '--kind', kind, '--as', 'Perf Agent'];
		if (kind === 'objection' || kind === 'suggestion') args.push('--severity', SEVERITIES[n % SEVERITIES.length]);
		n++;
		const id = loom(args).split(/\s+/)[0];
		if (/^a-\d{4}-/.test(id)) made.push(id);
	}
	for (const id of made.slice(0, 10)) loom(['annotate', '--reply', id, 'A reply with $x^2$ in it.', '--as', 'Perf Reader']);
	for (const id of made.slice(10, 18)) loom(['annotate', '--resolve', id, 'Addressed.', '--as', 'Perf Reader']);

	const pdf = master.pdf ? join(root, 'build', master.pdf) : '';
	const m = JSON.parse(readFileSync(join(root, 'build', 'manifest.json'), 'utf8')) as Manifest;
	const work = Object.keys(m.references).sort()[0];
	if (pdf && existsSync(pdf) && work) loom(['library', 'add', pdf, '--for', work, '--force']);
	loom(['build']);
	if (made.length < 20) throw new Error(`only ${made.length} annotations could be seeded into ${source}`);
}
