import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Manifest } from '$lib/manifest/types';
import { placeUrl } from '$lib/nav';
import { keepRow, ledgerRows, needsYou, problemsOf } from '$lib/library';
import { reachedExternal } from '$lib/reached';
import { fileHref } from '$lib/shell/files';

const fixture = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;

describe('Review opens a thing where it lives (plan 0.25.1)', () => {
	it('opens a result in the document that reads it, the default first, with a named note open there', () => {
		expect(placeUrl(fixture, 'sy-0001')).toBe('/master/drafting/main#sy-0001');
		expect(placeUrl(fixture, 'sy-0001', 'a-1')).toBe('/master/drafting/main?note=a-1#sy-0001');
		// a proof is read through the statement that owns it, at its own place
		expect(placeUrl(fixture, 'sy-0002/proof')).toBe('/master/drafting/main#sy-0002-proof');
		// a note on a whole document opens the document
		expect(placeUrl(fixture, 'drafting/main.tex', 'a-2')).toBe('/master/drafting/main?note=a-2');
	});

	it("opens a result of an agent's copy in the copy, and sends a cited work's result where it always went", () => {
		expect(placeUrl(fixture, 'sy-0002-ai')).toBe('/master/.loom/copies/aidoc#sy-0002-ai');
		// the person's own document is preferred where both read a result
		expect(placeUrl(fixture, 'sy-0001')).toBe('/master/drafting/main#sy-0001');
		expect(placeUrl(fixture, 'Kre99-sec-1')).not.toContain('/master/');
	});

	it('opens a project file the way the tree does', () => {
		const at = (path: string) => fileHref(fixture, fixture.files!.find((f) => f.path === path)!);
		expect(at('drafting/main.tex')).toBe('/master/drafting/main');
		expect(at('research-state.md')).toBe('/page/state');
		expect(at('README.md')).toContain('README.md');
	});
});

describe("Library's count is its page's \"needs you\"", () => {
	it('counts the works the page shows under needs you, from what stands on disk', () => {
		const rows = ledgerRows(fixture, reachedExternal(fixture));
		const page = rows.filter((r) => keepRow(r, problemsOf(fixture, fixture.references[r.citekey]), 'needs-you')).length;
		expect(needsYou(fixture)).toBe(page);
	});
});
