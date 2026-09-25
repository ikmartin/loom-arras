// Plan 0.9.5 §7: arras's core is host-neutral. The shells and the app served with loom are one host among others, and the core must not assume it is the only one. Like the forbidden-words guard beside it (Chapter 10.8), this is a boundary test rather than a style test: it exists so a boundary already decided is not eroded one plan at a time.
//
// The boundary over `src/lib/`, of which RULES checks what a pattern can:
//   - no write to `:root` or `document.documentElement`; tokens go on a class the host applies, and preferences are set on a root the host owns.
//   - no origin-absolute URL or route literal; every path comes from `$lib/paths`, and every URL a widget emits comes from an injected policy, as LocalGraphPanel's `hrefFor` does.
//   - no new module-level singleton holding corpus state; one corpus per page is a host's choice.
//   - no publisher's name, scheme or command, in code or in copy; those arrive in the manifest. (The forbidden-words guard covers the vocabulary; this one covers the URL scheme.)
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
		// prefs applies the host's chosen theme to the root the host owns, which for the app served with loom is `documentElement` -- the same element carrying `.arras`. This is not debt: seam 2 was declined (0.9.5 §8), the app is a host, and a host owning its own root is the arrangement, not a step towards another one.
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
		// No exemption. The work-link scheme is `cited:` (specs/dialect.md §2.13, DR-166): the interface's own, named for what it points at rather than for whoever wrote the corpus. `worklink.ts` naming it is arras implementing the format, and nothing in `src/` names a publisher.
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

/** Every `file: rule` pair the rules flag in `files`, each given as `[path, text]`. */
function offenders(files: [string, string][]): string[] {
	const out: string[] = [];
	for (const [file, text] of files) {
		for (const rule of RULES) {
			if (rule.exempt?.(file)) continue;
			if (rule.re.test(text)) out.push(`${file}: ${rule.name}`);
		}
	}
	return out;
}

/** Per rule: a line it must flag, a line it must pass, and the files exempt from it among `PROBES`. */
const CASES: { name: string; bad: string; good: string; exempt: string[] }[] = [
	{ name: 'writes to the document root', bad: 'document.documentElement.dataset.theme = t;', good: 'host.dataset.theme = t;', exempt: ['src/lib/prefs.svelte.ts'] },
	{ name: 'declares tokens on :root', bad: ':root { --ink: black; }', good: '.arras { --ink: black; }', exempt: [] },
	{ name: 'hard-codes the build directory', bad: "fetch('/build/' + path)", good: 'fetch(dataUrl(path))', exempt: [OWNS_PATHS] },
	{ name: 'writes an origin-absolute route', bad: '<a href="/">home</a>', good: "<a href={route('/')}>home</a>", exempt: [OWNS_PATHS] },
	{ name: 'returns an origin-absolute path', bad: "return '/node/' + key;", good: "return route('/node/' + key);", exempt: [OWNS_PATHS] },
	{ name: "names a publisher's URL scheme", bad: "const PREFIX = 'loom:';", good: "const PREFIX = 'cited:';", exempt: [] }
];

const PROBES = ['src/lib/prefs.svelte.ts', OWNS_PATHS, 'src/lib/nav.ts'];

describe('host neutrality', () => {
	it('src/lib/ assumes nothing about the host it is rendered in', () => {
		const files = walk('src/lib');
		expect(files).toContain(OWNS_PATHS);
		expect(offenders(files.map((f) => [f, readFileSync(f, 'utf8')]))).toEqual([]);
	});

	it('flags what each rule forbids, passes its composed form, and exempts only the files it names', () => {
		expect(CASES.map((c) => c.name)).toEqual(RULES.map((r) => r.name));
		for (const { name, bad, good, exempt } of CASES) {
			const rule = RULES.find((r) => r.name === name)!;
			expect(bad, name).toMatch(rule.re);
			expect(good, name).not.toMatch(rule.re);
			expect(typeof rule.exempt, name).toBe(exempt.length ? 'function' : 'undefined');
			expect(PROBES.filter((f) => rule.exempt?.(f)), name).toEqual(exempt);
		}
	});

	it('reports a planted violation of every rule, except in the file exempt from it', () => {
		const planted = 'src/lib/planted.ts';
		expect(offenders(CASES.map((c) => [planted, c.bad]))).toEqual(CASES.map((c) => `${planted}: ${c.name}`));
		expect(offenders(CASES.flatMap((c) => c.exempt.map((f): [string, string] => [f, c.bad])))).toEqual([]);
	});
});
