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
/** The token file declares the palette; `:root` there is the declaration a host overrides, not a write by the core. */
const OWNS_TOKENS = 'src/lib/theme.css';

interface Rule {
	name: string;
	re: RegExp;
	exempt?: (file: string) => boolean;
}

const RULES: Rule[] = [
	{
		name: 'writes to the document root',
		re: /documentElement/,
		// prefs applies the host's chosen theme to the root it was given; until seam 2 it is the app's own root
		exempt: (f) => f === 'src/lib/prefs.svelte.ts'
	},
	{
		name: 'declares tokens on :root',
		re: /:root/,
		exempt: (f) => f === OWNS_TOKENS
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
		name: "names a publisher's URL scheme",
		re: /['"`]loom:/,
		// The scheme is a publisher's name compiled into the core and belongs in `manifest.publisher`; moving it is
		// R2b's, in the plan that follows. These three are the whole of it as of 2026-09-17, named so that the guard
		// catches a fourth and so that emptying this list is the visible end of the job.
		exempt: (f) => PENDING_R2B.includes(f)
	}
];

const PENDING_R2B = ['src/lib/worklink.ts', 'src/lib/manifest/loader.ts', 'src/lib/components/PdfViewer.svelte'];

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

	it('fails when a token is declared on the document root outside the token file', () => {
		const rule = RULES.find((r) => r.name === 'declares tokens on :root')!;
		expect(rule.re.test(':root { --ink: black; }')).toBe(true);
		expect(rule.exempt!(OWNS_TOKENS)).toBe(true);
	});
});
