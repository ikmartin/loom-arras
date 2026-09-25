// Book 10.8: arras never contains a source-language parser or loom code, and names none of loom's operations as its own. The word quilt is arras's too since plan 0.14 gave the quilt's own things a link scheme, `quilt:` (DR-270-ikmartin); the guard enforces the rest: the loom-only operations, and every `loom <command>` phrase; advice that names a command reaches the viewer as a diagnostic's fix, never as arras's own words. Fixture data and manifest-supplied labels are outside src/ and untouched.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const FORBIDDEN = [
	/\batomize\b/i,
	/\bunravel\b/i,
	/\bloom\s+(init|doctor|upgrade|new|id|import|draft|canonize|stamp|fork|revert|live|linearize|history|search|delete|deps|build|bundle|compile|lint|check|status|serve|accept|annotate|ai|digest)\b/i
];

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (/\.(ts|js|svelte|css|html)$/.test(name) && !/\.(spec|test)\./.test(name)) out.push(p);
	}
	return out;
}

/** Every `file: pattern` pair the forbidden words flag in `files`, each given as `[path, text]`. */
function offenders(files: [string, string][]): string[] {
	const out: string[] = [];
	for (const [file, text] of files) for (const re of FORBIDDEN) if (re.test(text)) out.push(`${file}: ${re}`);
	return out;
}

describe('boundary', () => {
	it('src/ contains none of the forbidden words', () => {
		const files = walk('src');
		expect(files).toContain(join('src', 'lib', 'paths.ts'));
		expect(offenders(files.map((f) => [f, readFileSync(f, 'utf8')]))).toEqual([]);
	});

	it('reports a planted use of every forbidden word, and passes the words arras may use', () => {
		const planted: [string, string][] = [
			['a.ts', 'atomize the file'],
			['b.ts', 'unravel it'],
			['c.svelte', 'run `loom lint` to see']
		];
		expect(offenders(planted)).toEqual(planted.map(([f], i) => `${f}: ${FORBIDDEN[i]}`));
		expect(offenders([['d.ts', "a quilt: link names what the loom of the corpus wrote"]])).toEqual([]);
	});
});
