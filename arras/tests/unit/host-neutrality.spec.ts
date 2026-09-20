// Plan 0.9.5 §7: arras's core is host-neutral. The shells and the app served with loom are one host among others,
// and the core must not assume it is the only one. Like the forbidden-words guard beside it (Chapter 10.8), this is a
// boundary test rather than a style test: it exists so a boundary already decided is not eroded one plan at a time.
//
// Four rules over `src/lib/`:
//   - no write to `:root` or `document.documentElement`; tokens go on a class the host applies, and preferences are
//     set on a root the host owns.
//   - no origin-absolute URL or route literal; every path comes from `$lib/paths`, and every URL a widget emits comes
//     from an injected policy, as LocalGraphPanel's `hrefFor` already does.
//   - no new module-level singleton holding corpus state; one corpus per page is a host's choice.
//   - no publisher's name, scheme or command, in code or in copy; those arrive in the manifest. (The forbidden-words
//     guard covers the vocabulary; this one covers the URL scheme.)
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/** `src/lib/paths.ts` is where the exceptions live: it is the one module that may name the defaults. */
const OWNS_PATHS = 'src/lib/paths.ts';

interface Rule {
	name: string;
	re: RegExp;
	exempt?: (file: string) => boolean;
}

const RULES: Rule[] = [
	{
		name: 'writes to the document root',
		re: /documentElement/,
		// prefs applies the host's chosen theme to the root the host owns, which for the app served with loom is
		// `documentElement` -- the same element carrying `.arras`. This is not debt: seam 2 was declined (0.9.5 §8),
		// the app is a host, and a host owning its own root is the arrangement, not a step towards another one.
		exempt: (f) => f === 'src/lib/prefs.svelte.ts'
	},
	{
		// No exemption: the tokens live on `.arras`, the class a host applies to the element it owns (0.11 Part I).
		name: 'declares tokens on :root',
		re: /:root/
	},
	{
		name: 'hard-codes the build directory',
		re: /['"`]\/build\//,
		exempt: (f) => f === OWNS_PATHS
	},
	{
		// `/[a-z]` would miss a bare `href="/"`, which is just as origin-absolute and was how two shells linked home.
		name: 'writes an origin-absolute route',
		re: /(?:href|url|src)\s*[=:]\s*['"`]\/(?![/*])/i,
		exempt: (f) => f === OWNS_PATHS
	},
	{
		name: "returns an origin-absolute path",
		re: /return\s+['"`]\/[a-z]/,
		exempt: (f) => f === OWNS_PATHS
	},
	{
		// No exemption. The work-link scheme is `cited:` (specs/dialect.md §2.13, DR-166): the interface's own, named
		// for what it points at rather than for whoever wrote the corpus. `worklink.ts` naming it is arras
		// implementing the format, and there is nothing left in `src/` that names a publisher.
		name: "names a publisher's URL scheme",
		re: /['"`]loom:/
	}
];

function walk(dir: string, out: string[] = []): string[] {
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) walk(p, out);
		else if (/\.(ts|js|svelte|css)$/.test(name) && !/\.(spec|test)\./.test(name)) out.push(p);
	}
	return out;
}

describe('host neutrality', () => {
	it('src/lib/ assumes nothing about the host it is rendered in', () => {
		const offenders: string[] = [];
		for (const file of walk('src/lib')) {
			const text = readFileSync(file, 'utf8');
			for (const rule of RULES) {
				if (rule.exempt?.(file)) continue;
				if (rule.re.test(text)) offenders.push(`${file}: ${rule.name}`);
			}
		}
		expect(offenders).toEqual([]);
	});

	it('fails when an absolute build path is added to the core', () => {
		const rule = RULES.find((r) => r.name === 'hard-codes the build directory')!;
		expect(rule.re.test(`fetch('/build/' + path)`)).toBe(true);
		expect(rule.re.test(`fetch(dataUrl(path))`)).toBe(false);
	});

	it('fails when a token is declared on the document root, with nothing exempt', () => {
		const rule = RULES.find((r) => r.name === 'declares tokens on :root')!;
		expect(rule.re.test(':root { --ink: black; }')).toBe(true);
		expect(rule.re.test('.arras { --ink: black; }')).toBe(false);
		expect(rule.exempt).toBeUndefined();
	});

	it('still forbids a publisher scheme, now that nothing is exempt from it', () => {
		const rule = RULES.find((r) => r.name === "names a publisher's URL scheme")!;
		expect(rule.re.test(`const PREFIX = 'loom:';`)).toBe(true);
		expect(rule.re.test(`const PREFIX = 'cited:';`)).toBe(false);
		expect(rule.exempt).toBeUndefined();
	});
});
