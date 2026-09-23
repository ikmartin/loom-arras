import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

const routes: [string, string][] = [
	['/node/sy-0003', 'Parity'],
	['/node/sy-0200', 'Results'],
	['/master/main', 'Widgets, gadgets'],
	['/library/Kre99', 'Cycle groups'],
	['/review', 'Review'],
	['/problems', 'Problems'],
	['/blockers', 'Review'],
	['/graph', 'Graph'],
	['/threads', 'Threads'],
	['/tags', 'Tags'],
	['/tag/orbits', '#orbits'],
	['/taxa', 'Taxa'],
	['/taxon/lemma', 'Lemma'],
	['/library', 'Library'],
	['/loose', 'Not in any document']
];

for (const [path, heading] of routes) {
	test(`route ${path} renders`, async ({ page }) => {
		await page.goto(path);
		await expect(page.locator('main h1').first()).toContainText(heading);
	});
}

test('node page shows the fragment with typeset math and its proofs', async ({ page }) => {
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .env[data-id="sy-0003"]')).toBeVisible();
	await expect(page.locator('.fragment details.env-proof')).toHaveCount(2);
	await expect(page.locator('.fragment mjx-container').first()).toBeVisible();
	await expect(page.locator('.fragment .env-label .number')).toHaveText('2.1');
});

test('master view expands inclusions in place', async ({ page }) => {
	await page.goto('/master/main');
	await expect(page.locator('.fragment .included[data-file="nodes/sy-0002.tex"]')).toBeVisible();
	await expect(page.locator('.fragment section[data-id="sy-0300"] h2')).toBeVisible();
});

test('problems page lists every diagnostic code', async ({ page }) => {
	await page.goto('/problems');
	const codes = new Set<string>(manifest.diagnostics.map((d: { code: string }) => d.code));
	for (const code of codes) await expect(page.locator(`main h2 code`, { hasText: code }).first()).toBeVisible();
});

test('unknown state labels and codes render generically', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.keys['sy-0003'].state = 'mysterious';
		m.diagnostics.push({ severity: 'info', code: 'other:code', message: 'from another publisher', locations: [], keys: [] });
		await route.fulfill({ json: m });
	});
	await page.goto('/node/sy-0003');
	await expect(page.locator('.chip', { hasText: 'statement mysterious' })).toBeVisible();
	await page.goto('/problems');
	await expect(page.locator('main h2 code', { hasText: 'other:code' })).toBeVisible();
});

test('incoming review stays separate from recorded states and opens a document comparison', async ({ page }) => {
	let incorporated: Record<string, string> | null = null;
	await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['sync-incorporate'] } }));
	await page.route('**/_api/sync-incorporate', async (route) => {
		incorporated = route.request().postDataJSON();
		await route.fulfill({ json: { ok: true, result: { source_commit: 'c'.repeat(40), sync_commit: 'd'.repeat(40), integrated: 'b'.repeat(40), paths: ['drafting/main.tex'] } } });
	});
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.macros.sets['incoming:test'] = m.macros.default;
		m.incoming = {
			remote: 'origin', branch: 'main', base: 'a'.repeat(40), commit: 'b'.repeat(40), observed: '2026-09-21T15:00:00Z',
			files: [{ status: 'M', path: 'drafting/main.tex' }, { status: 'M', path: 'references.bib', diff: '+@book{source,title={A collaborator reference}}' }],
			changes: [{
				key: 'sy-0003', kind: 'edited', local_changed: false, conflict: false, already_local: false,
				local: 'fragments/review/800fd03b12dbadcd3f9d-current.html',
				incoming: 'fragments/review/800fd03b12dbadcd3f9d-accepted.html', incoming_macros: 'incoming:test',
				affected: [{ key: 'sy-0004', citation: null }]
			}]
		};
		await route.fulfill({ json: m });
	});
	await page.goto('/review?show=incoming');
	await expect(page.getByTestId('incoming-sy-0003')).toBeVisible();
	await expect(page.getByRole('navigation', { name: 'Review views' }).getByRole('link', { name: 'Incoming (1)' })).toBeVisible();
	await expect(page.getByTestId('review-counts')).toHaveCount(0);
	await expect(page.getByTestId('incoming-incorporation')).toContainText('neither push nor accept mathematics');
	const files = page.getByRole('heading', { name: 'Changed source files' }).locator('xpath=following-sibling::ul[1]');
	await expect(files).toContainText('drafting/main.tex');
	await expect(files).toContainText('references.bib');
	const incorporationBeforeChange = await page.evaluate(() => {
		const action = document.querySelector('[data-testid="incoming-incorporation"]')!;
		const change = document.querySelector('[data-testid="incoming-sy-0003"]')!;
		return !!(action.compareDocumentPosition(change) & Node.DOCUMENT_POSITION_FOLLOWING);
	});
	expect(incorporationBeforeChange).toBe(true);
	await page.getByRole('button', { name: 'Incorporate pull' }).click();
	await expect.poll(() => incorporated).toEqual({ incoming: 'b'.repeat(40), base: 'a'.repeat(40) });
	await page.getByText('references.bib', { exact: true }).last().click();
	await expect(page.locator('.incoming-file-diff')).toContainText('A collaborator reference');
	await page.getByTestId('incoming-sy-0003').locator('h2 a').click();
	await expect(page).toHaveURL(/incoming=sy-0003/);
	await expect(page.getByTestId('incoming-comparison')).toBeVisible();
});

test('Needs review separates the block queue, pending OK, and attention', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.unresolved = [
			{ key: 'sy-0001', status: 'needs-review', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: true, local_changed: false, invalidated: false },
			{ key: 'sy-0002', status: 'ok', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: false, invalidated: false },
			{ key: 'sy-0003', status: 'requires-attention', cause: 'earlier-change', pull: '', changed_text: false, invalidated: false }
		];
		await route.fulfill({ json: m });
	});
	await page.goto('/review?show=needs-review');
	await expect(page.getByRole('navigation', { name: 'Review views' }).getByRole('link', { name: 'Needs Review (1)' })).toBeVisible();
	await expect(page.getByText('1 need review · 1 pending OK · 1 require attention')).toBeVisible();
	await expect(page.getByRole('heading', { name: /needs review/i })).toBeVisible();
	await expect(page.getByRole('heading', { name: /pending ok/i })).toBeVisible();
	await expect(page.getByRole('heading', { name: /requires attention/i })).toBeVisible();
	await page.getByRole('button', { name: 'Start review' }).click();
	await expect(page.getByTestId('guided-review')).toContainText('sy-0001');
	await expect(page.getByTestId('guided-review')).toContainText('Incoming pull');
	await page.getByRole('button', { name: 'Return to Needs review' }).click();
	await expect(page.getByTestId('guided-review')).toHaveCount(0);
	await page.getByRole('button', { name: 'sy-0003' }).click();
	await expect(page.getByTestId('guided-review')).toContainText('sy-0003');
	await expect(page.getByRole('button', { name: 'Mark OK' })).toHaveCount(0);
});

test('guided review highlights a dependent citation and distinguishes local edits', async ({ page }) => {
	await page.route('**/fragments/nodes/sy-0002.html', async (route) => {
		const response = await route.fetch();
		const body = await response.text();
		const citation = '<a id="cite-nodes-sy-0002-tex-185-sy-0001-eq-fix"';
		expect(body).toContain(citation);
		await route.fulfill({ response, body: body.replace(citation, `<span style="display:block;height:1200px"></span>${citation}`) });
	});
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.unresolved = [
			{ key: 'sy-0002', status: 'needs-review', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: false, local_changed: true, invalidated: false },
			{ key: 'sy-0003', status: 'needs-review', cause: 'earlier-change', pull: '', changed_text: false, local_changed: true, invalidated: false }
		];
		await route.fulfill({ json: m });
	});
	await page.goto('/review?show=needs-review');
	await page.getByRole('button', { name: 'Start review' }).click();
	const guided = page.getByTestId('guided-review');
	await expect(guided).toContainText('Pull bbbbbbbbbbbb + local edits');
	await expect(guided.locator('#cite-nodes-sy-0002-tex-185-sy-0001-eq-fix')).toHaveClass(/review-citation-target/);
	const position = await guided.evaluate((section) => {
		const pane = section.querySelector('.guided-current')!;
		const citation = pane.querySelector('#cite-nodes-sy-0002-tex-185-sy-0001-eq-fix')!;
		return { scrollTop: pane.scrollTop, paneBottom: pane.getBoundingClientRect().bottom, citationTop: citation.getBoundingClientRect().top };
	});
	expect(position.scrollTop).toBeGreaterThan(0);
	expect(position.citationTop).toBeLessThan(position.paneBottom);
	await page.getByRole('button', { name: 'sy-0003' }).click();
	await expect(guided).toContainText('Local change');
	await expect(guided.locator('.review-citation-target')).toHaveCount(0);
	await expect(guided.locator('.guided-current')).toHaveJSProperty('scrollTop', 0);
	await page.getByRole('button', { name: 'sy-0002' }).click();
	await expect(guided.locator('.review-citation-target')).toHaveCount(1);
	const viewportPosition = await guided.evaluate((section) => {
		const pane = section.querySelector('.guided-current')!;
		const citation = pane.querySelector('.review-citation-target')!;
		return { paneTop: pane.getBoundingClientRect().top, citationTop: citation.getBoundingClientRect().top, viewportHeight: window.innerHeight };
	});
	expect(viewportPosition.paneTop).toBeGreaterThanOrEqual(0);
	expect(viewportPosition.citationTop).toBeGreaterThanOrEqual(0);
	expect(viewportPosition.citationTop).toBeLessThan(viewportPosition.viewportHeight);
});

test('interface version mismatch shows one diagnostic and nothing else', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.interface_version = 99;
		await route.fulfill({ json: m });
	});
	await page.goto('/node/sy-0003');
	await expect(page.locator('main h1')).toHaveText('Problems');
	await expect(page.locator('main code', { hasText: 'arras:interface-version' })).toBeVisible();
	await expect(page.locator('.fragment')).toHaveCount(0);
});

test('search finds by id, alias, title, and tag', async ({ page }) => {
	await page.goto('/');
	const data = await page.locator('ninja-keys').evaluate((el) => (el as unknown as { data: { id: string; keywords: string; title: string }[] }).data);
	expect(data.some((d) => d.id === 'sy-0002')).toBe(true);
	expect(data.some((d) => d.keywords.includes('def:gadget'))).toBe(true);
	expect(data.some((d) => d.title.includes('Parity'))).toBe(true);
	expect(data.some((d) => d.keywords.includes('orbits'))).toBe(true);
});

test('live reload follows the manifest only', async ({ page }) => {
	let version = 0;
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		if (version > 0) m.corpus.root_label = 'Renamed corpus';
		await route.fulfill({ json: m });
	});
	await page.goto('/');
	await expect(page.locator('main h1')).toHaveText('Widgets, gadgets, and their fixed loci');
	version = 1;
	await expect(page.locator('main h1')).toHaveText('Renamed corpus', { timeout: 5000 });
});

test('marks and boxes on the annotated node; discarded hidden by default', async ({ page }) => {
	// the margin arrangement, which this test is about: a mark activates the box standing beside the node. The default
	// placement is `floating`, which opens a box over the text instead (plan 0.13 §7).
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'margin' })));
	await page.goto('/node/sy-0003');
	// Counted as "every open annotation on this key has a box", not as a literal, so adding one to the fixture does
	// not fail a test that is about marks and boxes agreeing.
	const open = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		// the panel is about the node, which means every key the node owns -- its statement and its proofs, which
		// carry ids of their own rather than a `/proof` suffix
		const keys = Object.entries(m.keys)
			.filter(([, k]: [string, any]) => k.node === 'sy-0003')
			.map(([id]) => id);
		return Object.values(m.annotations).filter(
			(a: any) => keys.includes(a.target.key) && !a.in_reply_to && !a.discarded
		).length;
	});
	expect(open).toBeGreaterThan(1);
	await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(open);
	// only the annotations that quote a phrase can be marked in the text
	await expect(page.locator('.fragment mark.annotation')).toHaveCount(2);
	await page.locator('.fragment mark.annotation').first().click();
	await expect(page.locator('article.box.active')).toHaveCount(1);
	await expect(page.locator('article.box.active > header .kind')).toHaveText('objection');
	await expect(page.locator('article.box.active .reply')).toHaveCount(1);
	// sy-000A's one annotation is discarded AND belongs to a closed session, so two filters hide it and the reader
	// must lift both. Closing a session hides its annotations (plan 0.13 §5), which is what closing one is for.
	await page.goto('/node/sy-000A');
	await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(0);
	// the closed section unfolds, and the setting inside it is what admits their annotations (plan 0.13.1)
	await page.getByTestId('show-closed').click();
	await page.getByTestId('closed-yes').click();
	await expect(page.getByTestId('annotation-list').locator('article.box')).toHaveCount(0); // still discarded
	await page.getByLabel('show discarded').check();
	await expect(page.getByTestId('annotation-list').locator('article.box.discarded')).toHaveCount(1);
});

test('review causes open rendered text beside its current context', async ({ page }) => {
	await page.goto('/review');
	await expect(page.getByTestId('review-counts')).toContainText('5 stale');
	const row = page.locator('table.list tr', { hasText: 'sy-0002/proof' });
	await expect(row).toContainText('sy-0001 via sy-0002');
	const stale = page.locator('table.list tr', { hasText: 'sy-0001' }).first();
	await expect(stale).toContainText('1 detached');
	await stale.getByRole('link', { name: 'text edit' }).click();
	await expect(page).toHaveURL(/\/master\/main\?review=sy-0001&cause=0#sy-0001$/);
	await expect(page.getByTestId('review-comparison').locator('.fragment')).toHaveAttribute('aria-busy', 'false');
	await expect(page.getByTestId('review-comparison')).toContainText('satisfying');
	await expect(page.getByTestId('review-comparison').locator('.math mjx-container')).not.toHaveCount(0);
	await expect(page.getByTestId('review-comparison').locator('.review-changed')).not.toHaveCount(0);
	await expect(page.getByTestId('review-comparison')).not.toContainText('\\providecommand');
	const comparisonLayout = await page.evaluate(() => {
		const document = window.document.querySelector('.gutters-host')!.getBoundingClientRect();
		const comparison = window.document.querySelector('.review-comparison')!.getBoundingClientRect();
		return { documentRight: document.right, comparisonLeft: comparison.left, pageOverflows: window.document.documentElement.scrollWidth > window.innerWidth };
	});
	expect(comparisonLayout.comparisonLeft).toBeGreaterThan(comparisonLayout.documentRight);
	expect(comparisonLayout.pageOverflows).toBe(false);
	await page.goto('/review');
	const dependent = page.locator('table.list tr', { hasText: 'sy-0002' }).first();
	await dependent.getByRole('link', { name: 'sy-0001', exact: true }).click();
	await expect(page).toHaveURL(/#cite-nodes-sy-0002-tex-185-sy-0001-eq-fix$/);
	await expect(page.locator('#cite-nodes-sy-0002-tex-185-sy-0001-eq-fix')).toHaveClass(/review-citation-target/);
	await expect(page.getByTestId('review-comparison')).toContainText('involution');
});

test('review panel explains itself and names the command behind each state', async ({ page }) => {
	await page.goto('/review');
	await expect(page.locator('p.lead')).toContainText('Recorded states are read from this corpus’s review history.');
	await page.getByTestId('help-review').click();
	const help = page.getByTestId('help-panel-review');
	await expect(help).toContainText('stale');
	await expect(help).toContainText('accept');
});

test('review statement badges agree with proved and settled counts', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = structuredClone(manifest);
		m.nodes['sy-0003'].derived = { proved: true, settled: true };
		m.nodes['sy-0002'].derived = { proved: true, settled: false };
		m.keys['sy-0002'].acceptance.fresh = true;
		await route.fulfill({ json: m });
	});
	await page.goto('/review');
	const counts = await page.getByTestId('review-counts').innerText();
	expect(counts).toContain('2 proved');
	expect(counts).toContain('3 settled');
	await expect(page.locator('#review-sy-0003 .badge .chip')).toHaveText(['accepted', 'proved', 'settled']);
	await expect(page.locator('#review-sy-0002 .badge .chip')).toHaveText(['accepted', 'proved']);
});

test('missing proof on a block leads to its review row', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = structuredClone(manifest);
		m.diagnostics.push({ severity: 'warning', code: 'loom:missing-proof', message: 'No proof attached', locations: [], keys: ['sy-0003'] });
		await route.fulfill({ json: m });
	});
	await page.goto('/node/sy-0003');
	await page.getByTestId('missing-proof').getByRole('link').click();
	await expect(page).toHaveURL(/\/review\?document=drafting%2Fmain\.tex#review-sy-0003$/);
	await expect(page.locator('#review-sy-0003')).toContainText('missing proof');
});

test("a work's page lists results with their citers, and the Library counts them", async ({ page }) => {
	await page.goto('/library/Kre99');
	const item = page.locator('li:has(> a:first-child[href="/node/Kre99-thm-2.1"])');
	await expect(item).toContainText('sy-000A'); // \cite[Theorem 2.1]{Kre99} resolved to this result by its locator
	await page.goto('/library');
	// one row per work, carrying what the two indexes carried between them: who cites it, and what has been read of it
	const row = page.locator('tr', { hasText: 'Kre99' });
	await expect(row).toContainText('sy-000A');
	await expect(row.locator('td.num').first()).toHaveText('2');
	await page.goto('/problems');
	await expect(page.getByText('names no result in the digest of Kre99').first()).toBeVisible();
});

test('a run is read as the document beside the report', async ({ page }) => {
	await page.goto('/threads');
	await expect(page.getByText('referee sy-0003').first()).toBeVisible();
	await page.goto('/thread/s-2026-09-16-0001');
	await expect(page.getByTestId('split-view')).toBeVisible();
	// the document on the left, the report on the right, and the report is rendered rather than named
	await expect(page.locator('.pane.content .fragment').first()).toBeVisible();
	await expect(page.getByTestId('report-step')).toHaveCount(1);
	await expect(page.locator('.pane.discussion').getByText('Major Issues')).toBeVisible();
	// a finding about the whole document comes first, in a section of its own
	await expect(page.getByTestId('document-findings')).toBeVisible();
	// the journal is thread.md under its real name, and it is a tab of the CONTENT pane: the report is the discussion
	// and never folds behind a control (plan 0.13 §7)
	await page.getByTestId('tab-journal').click();
	await expect(page.locator('.pane.content').getByTestId('journal').getByText('hostile review of the parity theorem')).toBeVisible();
	await expect(page.getByTestId('report-step')).toBeVisible();
	await expect(page.locator('.pane.discussion [role="tablist"]')).toHaveCount(0);
	await page.getByTestId('tab-document').click();
	await expect(page.locator('pre', { hasText: 'loom comment sy-0003' })).toHaveCount(1); // the log, collapsed by default
});

test('the panes point at each other', async ({ page }) => {
	// The gate of plan 0.11 Parts B and C: a finding scrolls the document to the sentence it is about, and a mark in
	// the document scrolls the report to the finding that made it. Without both, this is two pages sharing a route.
	//
	// Asserting that scrollTop merely changed is not enough -- a target already at the top of its pane moves nothing --
	// so each half asserts the thing the reader cares about: after the click, the target is inside its pane's box.
	const inPane = (el: Element) => {
		const pane = el.closest('.pane') as HTMLElement;
		const a = el.getBoundingClientRect();
		const b = pane.getBoundingClientRect();
		return a.top >= b.top - 2 && a.bottom <= b.bottom + 2;
	};

	await page.goto('/thread/s-2026-09-16-0001');
	const finding = page.locator('.pane.discussion [data-annotation-id]').first();
	await expect(finding).toBeVisible();
	const id = await finding.getAttribute('data-annotation-id');
	const mark = page.locator(`.pane.content [data-annotation~="${id}"]`).first();
	await expect(mark).toBeVisible();

	// a finding scrolls the document to its mark
	await page.locator('.pane.content').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await page.waitForTimeout(200);
	await finding.click();
	// polled, not slept: smooth scrolling takes as long as the machine's load makes it take, and a fixed 900 ms passed
	// alone and failed under the parallel suite
	await expect.poll(() => mark.evaluate(inPane), { timeout: 5000 }).toBe(true);

	// and a mark scrolls the report to its finding
	await page.locator('.pane.discussion').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await page.waitForTimeout(200);
	await mark.click();
	await expect.poll(() => finding.evaluate(inPane), { timeout: 5000 }).toBe(true);
});

test('a session that wrote no report keeps the list shape', async ({ page }) => {
	// One route, two renderings: a report is the thing that wants a document beside it, so a session that wrote none is
	// still a list. The condition was `kind !== 'comments'` until sessions replaced runs and loom began writing
	// `kind: "session"` for every thread (DR-207) — at which point this session rendered as an empty two-pane review.
	await page.goto('/thread/s-2026-09-15-0001');
	await expect(page.locator('main h1')).toBeVisible();
	await expect(page.getByTestId('split-view')).toHaveCount(0);
	// and it offers the permalink, which is where a session is read back whole
	await expect(page.getByRole('link', { name: 'read it as a session' })).toBeVisible();

	// the one that did write a report is the other rendering, from the same route
	await page.goto('/thread/s-2026-09-16-0001');
	await expect(page.getByTestId('split-view')).toBeVisible();
});


test('see also lists both directions and says where each node is reached', async ({ page }) => {
	await page.goto('/node/sy-0009');
	const list = page.getByTestId('relations-see');
	await expect(list.getByRole('link', { name: /Gadget/ })).toBeVisible();
	await expect(list).toContainText('drafting/main.tex'); // the related node is reached by the paper

	await page.goto('/node/sy-0008'); // the relation is declared on the other node and shows here too
	await expect(page.getByTestId('relations-see').getByRole('link', { name: /Loose/ })).toBeVisible();
	await expect(page.getByTestId('relations-see')).toContainText('no document'); // where a node is reached, or that nothing reaches it
});

test('an unknown relation kind renders as a labelled list of links', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const res = await route.fetch();
		const m = await res.json();
		m.relations = [{ from: 'sy-0003', to: 'sy-0001', kind: 'contradicts', src: { file: 'x', line: 1 } }];
		await route.fulfill({ response: res, json: m });
	});
	await page.goto('/node/sy-0003');
	const list = page.getByTestId('relations-contradicts');
	await expect(list).toBeVisible();
	await expect(list.getByRole('link').first()).toHaveAttribute('href', '/node/sy-0001');
});

test('a node can be read as it was written', async ({ page }) => {
	// Plan 0.11 Part E: the source is fetched one key at a time from build/source/, only when asked.
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .env').first()).toBeVisible();
	const toggle = page.getByTestId('source-toggle').first();
	await expect(toggle).toHaveText('source');
	await toggle.click();
	const verbatim = page.getByTestId('verbatim').first();
	await expect(verbatim).toBeVisible();
	await expect(verbatim).toContainText('\\begin{theorem}'); // the LaTeX, not the rendering
	await expect(page.locator('.fragment .env')).toHaveCount(0); // and the rendering stands aside
	await expect(toggle).toHaveText('rendered');
	await toggle.click();
	await expect(page.locator('.fragment .env').first()).toBeVisible();
});

test("a suggestion shows the text it proposes, and says where it would go", async ({ page }) => {
	await page.goto('/node/sy-0004');
	const payload = page.getByTestId('payload').first();
	await expect(payload).toBeVisible();
	await expect(payload).toHaveAttribute('data-placement', 'replace');
	await expect(payload).toContainText('disjoint union of orbits');
	await expect(page.getByTestId('severity').first()).toBeVisible();
});

test('a run lists the notation it introduced, and flags a symbol used twice', async ({ page }) => {
	// Plan 0.11 Part F. Notation belongs to an agent's prose, never to the quilt's own text, so the panel is on the run.
	await page.goto('/thread/s-2026-09-16-0001');
	const panel = page.getByTestId('notation');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('with two meanings');
	await panel.locator('summary').click();
	await expect(panel).toContainText('the number of two-element orbits');
	await expect(panel).toContainText('declared twice in this run with different meanings');
});

test('a node page answers both closure questions without leaving it', async ({ page }) => {
	// Plan 0.11 Part D: the graph says what this would disturb, the stack says what it rests on. Neither is a route.
	await page.goto('/node/sy-0003');
	// the graph could always be read and never entered
	const graphLink = page.locator('[data-testid="local-graph"] a, .rail a[href*="/node/"]').first();
	await expect(graphLink).toBeVisible();

	const opener = page.getByTestId('closure-open');
	await opener.locator('> summary').click();
	const panel = page.getByTestId('closure-panel');
	await expect(panel).toBeVisible();
	const shallow = await panel.locator('ol.stack > li').count();
	expect(shallow).toBeGreaterThan(1);
	await expect(panel.locator('ol.stack > li').last()).toHaveClass(/centre/); // the result read is last

	await page.getByTestId('closure-depth-2').click();
	expect(await panel.locator('ol.stack > li').count()).toBeGreaterThanOrEqual(shallow);
});

test('the viewer shows no editing affordance when the publisher serves none', async ({ page }) => {
	// Plan 0.11 Part H and specs/write-api.md §1: detected, never assumed. The e2e fixture is served by a static
	// preview with no write API, so every affordance must be absent -- which is also what a deployed static site gets.
	await page.goto('/node/sy-0003');
	await expect(page.locator('main h1')).toBeVisible();
	await expect(page.getByTestId('composer')).toHaveCount(0);
	await expect(page.getByTestId('refnote-accept')).toHaveCount(0);
});

test('a document carries annotations of its own', async ({ page }) => {
	// loom has written these since 0.6 -- `loom comment` has always taken a master path -- and no viewer showed one.
	await page.goto('/master/main');
	const box = page.getByTestId('document-annotations');
	await expect(box).toBeVisible();
	await expect(box).toContainText('which conventions it inherits');
	await expect(box.getByTestId('severity').first()).toHaveText('moderate');
});

test('a node shows the citations suggested for it and those already accepted', async ({ page }) => {
	await page.goto('/node/sy-0003');
	const notes = page.getByTestId('reference-notes');
	await expect(notes).toBeVisible();
	await expect(notes).toContainText('Accepted, not yet in the bibliography');
	await expect(notes).toContainText('identifier unconfirmed'); // a breadcrumb, never a second source of identity truth
	await page.goto('/node/sy-0002');
	await expect(page.getByTestId('reference-notes')).toContainText('Suggested citations');
});

test('the setting is one switch, applied everywhere', async ({ page }) => {
	// running-requests: "applied globally so that it affects the read display as well as the display of nodes."
	await page.goto('/master/main');
	await expect(page.locator('html')).toHaveAttribute('data-format', 'p1'); // the compiled page, by default
	const numbered = page.locator('.fragment .env-label .number').first();
	await expect(numbered).toBeVisible();

	await page.evaluate(() => {
		const p = JSON.parse(localStorage.getItem('arras.prefs') || '{}');
		localStorage.setItem('arras.prefs', JSON.stringify({ ...p, format: 'b2' }));
	});
	await page.goto('/master/main');
	await expect(page.locator('html')).toHaveAttribute('data-format', 'b2');
	await expect(page.locator('.fragment .env-label .number').first()).toBeHidden();

	// the same switch on a node's own page: a result does not change character with the page it stands on
	await page.goto('/node/sy-0003');
	await expect(page.locator('html')).toHaveAttribute('data-format', 'b2');
	await expect(page.locator('.fragment .env-label .number').first()).toBeHidden();
});

test('a floating box stays open when the reader looks elsewhere, and only its × closes it', async ({ page }) => {
	// The default placement. One-at-a-time closed a box whenever the reader clicked away, so a second annotation could
	// not be read beside the first and a click on the text lost what was open (plan 0.13 §7).
	await page.goto('/node/sy-0003');
	const marks = page.locator('.fragment mark.annotation');
	await expect(marks).toHaveCount(2);
	await marks.first().click();
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);

	// a second mark opens a second box rather than replacing the first
	await marks.nth(1).click();
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(2);

	// clicking the text backgrounds them; nothing closes
	await page.locator('.fragment p').first().click({ position: { x: 4, y: 4 } });
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(2);
	await expect(page.locator('.comment-slot.floating.behind')).toHaveCount(2);

	// and a box's own × is what closes it
	await page.locator('.comment-slot.expanded.floating').first().locator('.comment-close').click();
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
});

test('travel goes to the annotation and back, and says so when there is nowhere to go', async ({ page }) => {
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ comments: 'margin' })));
	await page.goto('/node/sy-0003');
	const mark = page.locator('.fragment mark.annotation').first();
	const id = await mark.evaluate((m) => (m as HTMLElement).dataset.annotation!.split(/\s+/)[0]);

	// a brief scroll then a flash, so the eye is told where it landed rather than searching the pane it was sent to
	await mark.dblclick();
	await expect(page.locator(`#ann-${id}`)).toHaveClass(/travelled/);

	// and back the other way, from the card to its place in the text
	await page.locator(`#ann-${id}`).dblclick();
	await expect(page.locator('.fragment mark.annotation.travelled')).toHaveCount(1);

	// where there is nothing to travel to, nothing moves and a notice says so. a-2026-09-16-0004 is on this node and
	// quotes nothing, so it has no mark in the text and no approximate destination is invented for it.
	const orphan = page.locator('article.box[data-annotation-id="a-2026-09-16-0004"]');
	await expect(orphan).toHaveCount(1);
	await orphan.dblclick();
	await expect(page.getByTestId('travel-nowhere')).toBeVisible();
	await expect(page.getByTestId('travel-nowhere')).toHaveCount(0, { timeout: 3000 });
});

test('expand all opens every annotation at its mark, and hide all closes them', async ({ page }) => {
	await page.goto('/master/main');
	await page.getByTestId('expand-all').waitFor();
	const boxes = page.locator('aside.comment-slot.expanded');
	await expect(boxes).toHaveCount(0);

	await page.getByTestId('expand-all').click();
	const opened = await boxes.count();
	expect(opened).toBeGreaterThan(1);

	// hide all is the escape hatch that clicking outside no longer provides
	await page.getByTestId('hide-all').click();
	await expect(boxes).toHaveCount(0);

	// and the same two are keys, which is why they are named in the buttons' tooltips
	await page.locator('.fragment').focus();
	await page.keyboard.press('e');
	await expect(boxes).toHaveCount(opened);
	await page.keyboard.press('h');
	await expect(boxes).toHaveCount(0);
});
