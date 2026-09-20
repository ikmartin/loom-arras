// Book 10.8: arras never contains a source-language parser, loom code, or loom's vocabulary. The manifest specification itself names fields `proofs`, `digest`, and a route `/digest/<citekey>`, and the Web Crypto API has `digest()`, so those two words are exempt (decision record DR-39); the guard enforces the rest: the word quilt, the loom-only operations, and every `loom <command>` phrase; advice that names a command reaches the viewer as a diagnostic's fix, never as arras's own words. Fixture data and manifest-supplied labels are outside src/ and untouched.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const FORBIDDEN = [
	/\bquilts?\b/i,
	/\batomize\b/i,
	/\bunravel\b/i,
	/\bloom\s+(init|doctor|upgrade|new|id|import|draft|canonize|stamp|fork|revert|live|linearize|history|search|delete|deps|build|bundle|compile|lint|check|status|serve|accept|comment|ai|digest)\b/i
];

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (/\.(ts|js|svelte|css|html)$/.test(name) && !/\.(spec|test)\./.test(name)) out.push(p);
	}
	return out;
}

describe('boundary', () => {
	it('src/ contains none of the forbidden words', () => {
		const offenders: string[] = [];
		for (const file of walk('src')) {
			const text = readFileSync(file, 'utf8');
			for (const re of FORBIDDEN) if (re.test(text)) offenders.push(`${file}: ${re}`);
		}
		expect(offenders).toEqual([]);
	});
});
