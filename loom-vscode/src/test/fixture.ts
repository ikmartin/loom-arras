// The workspaces the test runs open: a fresh copy of loom's synthetic quilt and a plain LaTeX folder, made by .vscode-test.mjs before VS Code starts.

import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

/** loom's committed synthetic quilt, relative to this compiled file (out/test/). */
export const SYNTHETIC = path.resolve(__dirname, '..', '..', '..', 'loom', 'tests', 'quilts', 'synthetic');

/** The `[quilt]` table's flat string values; a quilt's config holds nothing else there. */
function quiltTable(root: string): Record<string, string> {
	const keys: Record<string, string> = {};
	let section = '';
	for (const line of fs.readFileSync(path.join(root, 'config.toml'), 'utf8').split(/\r?\n/)) {
		const header = /^\s*\[([^\]]+)\]/.exec(line);
		if (header) {
			section = header[1].trim();
			continue;
		}
		const pair = /^\s*([\w-]+)\s*=\s*"([^"]*)"/.exec(line);
		if (section === 'quilt' && pair) {
			keys[pair[1]] = pair[2];
		}
	}
	return keys;
}

/** The quilt's main master relative to its root, as loom resolves it: `[quilt] main`, else `<drafting>/main.tex`. */
export function masterOf(root: string): string {
	const keys = quiltTable(root);
	const drafting = (keys.drafting ?? 'drafting').replace(/^\/+|\/+$/g, '') || 'drafting';
	return keys.main ?? `${drafting}/main.tex`;
}

/** Copy the synthetic quilt and write a plain folder under a new temp dir; throws, naming the cause, when the quilt has no master where the suite expects one. */
export function makeWorkspaces(): { quilt: string; plain: string } {
	const master = path.join(SYNTHETIC, masterOf(SYNTHETIC));
	if (!fs.existsSync(master)) {
		throw new Error(`loom's synthetic quilt has no master at ${master}; did the fixture layout change?`);
	}
	// real path: loom-lsp answers with symlink-resolved URIs, and macOS's tmpdir is under the /var -> /private/var link
	const base = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'loom-vscode-')));
	const quilt = path.join(base, 'synthetic');
	fs.cpSync(SYNTHETIC, quilt, { recursive: true });
	const plain = path.join(base, 'plain');
	fs.mkdirSync(plain);
	fs.writeFileSync(path.join(plain, 'paper.tex'), '\\documentclass{article}\n\\begin{document}\nAn ordinary LaTeX file, in no quilt. The extension must leave it alone.\n\\end{document}\n');
	return { quilt, plain };
}
