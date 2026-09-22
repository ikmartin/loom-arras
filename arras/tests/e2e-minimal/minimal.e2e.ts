// Plan 0.9.5 §11, checks 1 and 2: the app against the interface's floor.
//
// `tests/fixture-minimal` is written by nobody's publisher and omits eleven top-level sections outright rather than
// writing them empty, because absence is what the loader's `normalise()` widens the floor for and `{}` would have
// passed before it. The assertions here are deliberately thin: this suite exists to prove that nothing *crashes* and
// that no view is furniture over nothing, not to check any particular content. The conformance fixture's suite is
// where behaviour is asserted, and it must stay pointed at that fixture.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('tests/fixture-minimal/manifest.json', 'utf8'));

const FIXED = ['/', '/review', '/problems', '/blockers', '/graph', '/threads', '/tags', '/taxa', '/library', '/loose'];
const NAMED = [
	...Object.keys(manifest.nodes ?? {}).map((k) => '/node/' + encodeURIComponent(k)),
	...Object.keys(manifest.tags ?? {}).map((t) => '/tag/' + encodeURIComponent(t)),
	...Object.values(manifest.taxa ?? {}).map((t) => '/taxon/' + encodeURIComponent((t as { slug: string }).slug))
];
const ROUTES = [...FIXED, ...NAMED];

// A page's own noise is not the app's: MathJax and a fragment that a floor fixture legitimately lacks both log.
const IGNORED = /MathJax|favicon|404 \(Not Found\)|net::ERR_/i;

function watch(page: Page): string[] {
	const bad: string[] = [];
	page.on('console', (m) => {
		if (m.type() === 'error' && !IGNORED.test(m.text())) bad.push(`console: ${m.text()}`);
	});
	page.on('pageerror', (e) => bad.push(`pageerror: ${e.message}`));
	return bad;
}

for (const path of ROUTES) {
	test(`${path} renders against the floor`, async ({ page }) => {
		const bad = watch(page);
		await page.goto(path);
		await expect(page.locator('main')).toBeVisible();
		// the shell resolved: the loading placeholder is gone and a heading or an empty state stands in its place
		await expect(page.locator('main').getByText('Loading manifest…')).toHaveCount(0);
		expect(bad, `${path} logged errors`).toEqual([]);
	});
}

// Check 2 of §11, and R2b is done: the list of phrases awaiting it is gone rather than empty, because an empty list
// invites a fifth entry. "not yet compiled" became "not yet numbered" and is shown only where the corpus declares it
// has documents; "loose" became "not in a document" everywhere it was copy. Every phrase below is asserted absent.
const FORBIDDEN = ['not yet compiled', 'loose', 'working drafts', 'quilt', 'loom'];

for (const path of ROUTES) {
	test(`${path} speaks no publisher's vocabulary`, async ({ page }) => {
		await page.goto(path);
		await expect(page.locator('main')).toBeVisible();
		const text = ((await page.locator('main').textContent()) ?? '').toLowerCase();
		for (const word of FORBIDDEN) {
			expect(text, `${path} contains "${word}"`).not.toContain(word);
		}
		// Note what is NOT asserted: the home page renders `manifest.publisher.name`, and that is correct. A name read
		// from the manifest and shown as attribution is the viewer being neutral; a name compiled into the source is
		// the violation. Check 2 is about arras's own copy, which is why the list above is of literal words.
	});
}
