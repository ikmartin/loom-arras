import { expect, test } from '@playwright/test';
import { beside, pane } from '../workspace';
import { openPicker } from '../picker';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

const routes: [string, string][] = [
	['/node/sy-0003', 'Parity'],
	['/node/sy-0200', 'Results'],
	['/master/main', 'Widgets, gadgets'],
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
		// a node draws no heading of its own (the tab names it): its title is in its statement
		if (path.startsWith('/node/')) await expect(page.locator('[data-pane] .fragment').first()).toContainText(heading);
		else await expect(page.locator('main h1').first()).toContainText(heading);
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
	// a state loom never told arras about is still said, in the gutter Show ids opens, in its own word
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ ids: true })));
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .node-margin', { hasText: 'mysterious' }).first()).toBeVisible();
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
	await expect(page.getByTestId('review-counts')).toContainText('stale');
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

test('a node draws no annotation list: its marks open their boxes, and the discarded are in its context', async ({ page }) => {
	// A mark opens its annotation as a floating box over the text; `show all annotations` opens every one. Nothing below the node lists them again (phase 4).
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
	await expect(page.getByTestId('annotation-list')).toHaveCount(0);
	// only the annotations that quote a phrase can be marked in the text
	await expect(page.locator('.fragment mark.annotation')).toHaveCount(2);
	await page.locator('.fragment mark.annotation').first().click();
	const opened = page.locator('[data-testid="comment-expanded"] article.box');
	await expect(opened).toHaveCount(1);
	await expect(opened.locator('> header .kind')).toHaveText('objection');
	await expect(opened.locator('.reply')).toHaveCount(1);
	// the rail opens every one at once, each at its mark or beside its result's label
	await page.getByTestId('toggle-annotations').click();
	await expect(page.locator('[data-testid="comment-expanded"] article.box')).toHaveCount(open);
	// sy-000A's one annotation is discarded AND belongs to a closed session, so two filters hide it and the reader
	// must lift both. Closing a session hides its annotations (plan 0.13 §5), which is what closing one is for.
	await page.goto('/node/sy-000A' + beside('/context/sy-000A'));
	const context = pane(page, 1);
	await expect(context.getByTestId('context')).toBeVisible();
	await expect(context.getByTestId('show-discarded')).toHaveCount(0);
	// the closed section unfolds, and the setting inside it is what admits their annotations (plan 0.13.1)
	await openPicker(page);
	await page.getByTestId('show-closed').click();
	await page.getByTestId('closed-yes').click();
	await page.keyboard.press('Escape');
	// a quiet line in the context says how many were discarded, and shows them there
	await expect(context.getByTestId('show-discarded')).toHaveText('1 discarded — show');
	await context.getByTestId('show-discarded').click();
	await expect(context.getByTestId('discarded-list').locator('article.box.discarded')).toHaveCount(1);
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

test('a missing proof is said where the proof would be, and its diagnostic is in the context', async ({ page }) => {
	await page.route('**/build/manifest.json', async (route) => {
		const m = structuredClone(manifest);
		m.diagnostics.push({ severity: 'warning', code: 'loom:missing-proof', message: 'No proof attached', locations: [], keys: ['sy-0003'] });
		await route.fulfill({ json: m });
	});
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const said = pane(page, 0).getByTestId('missing-proof');
	await expect(said).toHaveText('No proof is attached.');
	// after the statement, not above it: the statement leads (N1)
	const statement = (await pane(page, 0).locator('.fragment .env[data-id="sy-0003"]').boundingBox())!;
	expect((await said.boundingBox())!.y).toBeGreaterThan(statement.y);
	await expect(pane(page, 1).getByTestId('context')).toContainText('No proof attached');
});

test("a work's page lists results with their citers, and the Library counts them", async ({ page }) => {
	await page.goto('/library/Kre99');
	await page.getByTestId('tab-digest').click();
	const item = page.locator('li:has(> a:first-child[href="/node/Kre99-thm-2.1"])');
	await expect(item).toContainText('sy-000A'); // \cite[Theorem 2.1]{Kre99} resolved to this result by its locator
	await page.goto('/library');
	// the ledger counts what was read off it and how much of that the corpus leans on; who cites it is the work's own Digest view
	await expect(page.getByTestId('digest-Kre99')).toHaveText('2');
	await expect(page.getByTestId('used-Kre99')).not.toHaveText('—');
	await page.goto('/problems');
	await expect(page.getByText('names no result in the digest of Kre99').first()).toBeVisible();
});

test("a session's run is read as what it did, the report beside the document", async ({ page }) => {
	await page.goto('/threads');
	await expect(page.getByText('referee sy-0003').first()).toBeVisible();
	// a run's old address is its session's, and it opens on the discussion (plan 0.13.3 E1)
	await page.goto('/thread/s-2026-09-16-0001');
	await expect(page.getByTestId('discussion')).toBeVisible();
	// the journal is in the transcript, in time, and no date is a raw timestamp
	await expect(page.getByTestId('discussion').getByText('hostile review of the parity theorem')).toBeVisible();
	expect(await page.getByTestId('discussion').innerText()).not.toMatch(/\d{4}-\d{2}-\d{2}T/);
	// what it did: a sentence from the record, what is still open, and the report rendered rather than named
	await page.getByTestId('tab-did').click();
	const did = page.getByTestId('session-did');
	await expect(did.getByTestId('session-said')).toContainText('findings');
	await expect(did.getByTestId('report-step')).toHaveCount(1);
	await expect(did.getByText('Major Issues')).toBeVisible();
	await expect(did.getByTestId('session-open')).toBeVisible();
	// the run log is the command line's, not a reader's question
	await expect(did.locator('pre', { hasText: 'loom comment' })).toHaveCount(0);
	expect(await did.innerText()).not.toMatch(/\d{4}-\d{2}-\d{2}T/);
});

test('the panes point at each other', async ({ page }) => {
	// A finding in what the session did opens the document it is about, at its mark, in the other pane; and the mark's
	// double-click travels back to the finding. The run page did this inside a private split; the workspace does it
	// across its two panes. Each half asserts the target ends up inside its pane's box, not merely that something scrolled.
	const inPane = (el: Element) => {
		const pane = el.closest('[data-pane] > .body') as HTMLElement;
		const a = el.getBoundingClientRect();
		const b = pane.getBoundingClientRect();
		return a.top >= b.top - 2 && a.bottom <= b.bottom + 2;
	};
	await page.goto('/master/main' + beside('/session/s-2026-09-16-0001?view=did'));
	await expect(page.getByTestId('session-open')).toBeVisible();
	await page.waitForSelector('[data-pane="0"] .fragment [data-annotation]');
	// the first finding with a mark in the text: one about the document as a whole has none
	const id = await page.evaluate(() => {
		for (const li of document.querySelectorAll('[data-testid="session-open"] li')) {
			const id = li.id.replace(/^ann-/, '');
			if (document.querySelector(`[data-pane="0"] [data-annotation~="${id}"]`)) return id;
		}
		return '';
	});
	expect(id).not.toBe('');
	const row = page.locator(`[id="ann-${id}"]`);
	const mark = page.locator(`[data-pane="0"] [data-annotation~="${id}"]`).first();

	await page.locator('[data-pane="0"] > .body').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await row.locator('button.finding').click();
	await expect.poll(() => mark.evaluate(inPane), { timeout: 5000 }).toBe(true);

	await page.locator('[data-pane="1"] > .body').evaluate((el) => (el.scrollTop = el.scrollHeight));
	await mark.dblclick();
	await expect.poll(() => row.evaluate(inPane), { timeout: 5000 }).toBe(true);
});

test('what a session did claims only what is recorded', async ({ page }) => {
	// A session that wrote no report has no report section and says so by saying nothing (P3); the one that did has one.
	await page.goto('/session/s-2026-09-15-0001?view=did');
	await expect(page.getByTestId('session-did')).toBeVisible();
	await expect(page.getByTestId('report-step')).toHaveCount(0);
	await page.goto('/session/s-2026-09-16-0001?view=did');
	await expect(page.getByTestId('report-step')).toHaveCount(1);
});

test('see also lists both directions and says where each node is reached', async ({ page }) => {
	await page.goto('/node/sy-0009' + beside('/context/sy-0009'));
	const list = page.getByTestId('relations-see');
	await expect(list.locator('a[href$="/node/sy-0008"]')).toBeVisible();
	await expect(list).toContainText('drafting/main.tex'); // the related node is reached by the paper

	await page.goto('/node/sy-0008' + beside('/context/sy-0008')); // the relation is declared on the other node and shows here too
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
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const list = page.getByTestId('relations-contradicts');
	await expect(list).toBeVisible();
	await expect(list.getByRole('link').first()).toHaveAttribute('href', '/node/sy-0001');
});

test('a node can be read as it was written', async ({ page }) => {
	// Plan 0.11 Part E: the source is fetched one key at a time from build/source/, only when asked.
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .env').first()).toBeVisible();
	const toggle = page.getByTestId('source-toggle').first();
	await expect(toggle).toHaveText('verbatim code');
	await toggle.click();
	const verbatim = page.getByTestId('verbatim').first();
	await expect(verbatim).toBeVisible();
	await expect(verbatim).toContainText('\\begin{theorem}'); // the LaTeX, not the rendering
	await expect(page.locator('.fragment .env')).toHaveCount(0); // and the rendering stands aside
	await expect(toggle).toHaveText('rendered latex');
	await toggle.click();
	await expect(page.locator('.fragment .env').first()).toBeVisible();
});

test("a suggestion shows the text it proposes, and says where it would go", async ({ page }) => {
	await page.goto('/node/sy-0004');
	await page.getByTestId('toggle-annotations').click();
	const payload = page.getByTestId('payload').first();
	await expect(payload).toBeVisible();
	await expect(payload).toHaveAttribute('data-placement', 'replace');
	await expect(payload).toContainText('disjoint union of orbits');
	await expect(page.getByTestId('severity').first()).toBeVisible();
});

test('a run lists the notation it introduced, and flags a symbol used twice', async ({ page }) => {
	// Plan 0.11 Part F. Notation belongs to an agent's prose, never to the quilt's own text, so the panel is on the run.
	await page.goto('/session/s-2026-09-16-0001?view=did');
	// beneath the report, where it is consulted
	const panel = page.getByTestId('notation');
	await expect(panel).toBeVisible();
	await expect(panel).toContainText('with two meanings');
	await panel.locator('summary').click();
	await expect(panel).toContainText('the number of two-element orbits');
	await expect(panel).toContainText('declared twice in this run with different meanings');
});

test('a node page answers both closure questions without leaving it', async ({ page }) => {
	// Plan 0.11 Part D: the graph says what this would disturb, the stack says what it rests on. Neither is a route.
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	// the graph could always be read and never entered; it stands in the node's context, beside it
	const graphLink = page.getByTestId('context').locator('[data-testid="local-graph"] a').first();
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
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
	await expect(pane(page, 1).getByTestId('reference-notes')).toBeVisible();
	// no tools to write with, in the rail or on the page, and no verbs on what is written
	await expect(page.getByTestId('tool-select')).toHaveCount(0);
	await expect(page.getByTestId('refnote-accept')).toHaveCount(0);
});

test('a document carries annotations of its own, and they are read beside it', async ({ page }) => {
	// loom has written these since 0.6 -- `loom comment` has always taken a master path. They used to open a block above
	// the document, which put a remark about the whole paper on its title and sized a report like a sentence; the
	// discussion pane is where a document's own annotations are read, because that is the surface built for length.
	// The discussion is scoped by session (plan 0.13.3 E4), so they are read in the session's discussion beside it.
	await page.goto('/master/main' + beside('/session/s-2026-09-16-0001'));
	await expect(page.getByTestId('document-annotations')).toHaveCount(0);
	const pane = page.getByTestId('discussion');
	// the discussion lists everything written in the session, the document's own among them, so it is found by its text
	// rather than by being first; the list is compact items, not the boxes the retired block drew
	await expect(pane).toContainText('which conventions it inherits');
	await expect(pane.locator('li', { hasText: 'which conventions it inherits' })).toHaveCount(1);
});

test("a node's context shows the citations suggested for it and those already accepted", async ({ page }) => {
	await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
	const notes = pane(page, 1).getByTestId('reference-notes');
	await expect(notes).toBeVisible();
	await expect(notes).toContainText('Accepted, not yet in the bibliography');
	await expect(notes).toContainText('identifier unconfirmed'); // a breadcrumb, never a second source of identity truth
	await page.goto('/node/sy-0002' + beside('/context/sy-0002'));
	await expect(pane(page, 1).getByTestId('reference-notes')).toContainText('Suggested citations');
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

test('two floating boxes are open at once, its × closes one, and a click away closes them', async ({ page }) => {
	// The default placement. One-at-a-time could not show a second annotation beside the first, which is why several
	// may be open. Clicking away closes them: backgrounding left a clipped, faded stub that read as a ghost, or as a
	// doubled border under the box in front (amends DR-202).
	await page.goto('/node/sy-0003');
	const marks = page.locator('.fragment mark.annotation');
	await expect(marks).toHaveCount(2);
	await marks.first().click();
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);

	// a second mark opens a second box rather than replacing the first
	await marks.nth(1).click();
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(2);

	// a box's own × closes just that one
	await page.locator('.comment-slot.expanded.floating').first().locator('.comment-close').click();
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);

	// and clicking the text closes what is left, leaving no ghost behind
	await page.locator('.fragment p').first().click({ position: { x: 4, y: 4 } });
	await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(0);
	await expect(page.locator('.comment-slot.floating.behind')).toHaveCount(0);
});

test('travel goes from a mark to its finding, and says so when there is nowhere to go', async ({ page }) => {
	// alone, a node lists no annotations, so a mark has nowhere to travel to, and a notice says so rather than inventing a place
	await page.goto('/node/sy-0003');
	const mark = page.locator('.fragment mark.annotation').first();
	const id = await mark.evaluate((m) => (m as HTMLElement).dataset.annotation!.split(/\s+/)[0]);
	await mark.dblclick();
	await expect(page.getByTestId('travel-nowhere')).toBeVisible();
	await expect(page.getByTestId('travel-nowhere')).toHaveCount(0, { timeout: 3000 });

	// beside the session that wrote it, a brief scroll then a flash on the finding, so the eye is told where it landed
	await page.goto('/node/sy-0003' + beside('/session/s-2026-09-16-0001?view=did'));
	await pane(page, 0).locator('.fragment mark.annotation').first().dblclick();
	await expect(pane(page, 1).locator(`#ann-${id}`)).toHaveClass(/travelled/);
});

test('e opens every annotation at its mark, and h closes them', async ({ page }) => {
	// The document view draws no buttons for these. They were a row across the top of every document, ahead of its
	// title, for an action wanted occasionally -- so the keys are the whole affordance here until they have a home
	// that is not the reader's way.
	await page.goto('/master/main');
	await page.waitForSelector('.fragment mjx-container');
	const boxes = page.locator('aside.comment-slot.expanded');
	await expect(page.getByTestId('content-head')).toHaveCount(0);
	await expect(boxes).toHaveCount(0);

	await page.locator('.fragment').focus();
	await page.keyboard.press('e');
	const opened = await boxes.count();
	expect(opened).toBeGreaterThan(1);

	// h is the escape hatch that clicking outside no longer provides
	await page.keyboard.press('h');
	await expect(boxes).toHaveCount(0);
});

test('a citation opens the cited paper at the result, not the digest node', async ({ page }) => {
	// `[1, Theorem 2.1]` names a theorem in a paper, so where a copy is filed the link goes to the paper at that result.
	// The digest node's page renders loom's record of it -- the LaTeX, the provenance, what depends on it -- which is a
	// thing to go and look at and not what the citation names.
	await page.route('**/build/manifest.json', async (route) => {
		const res = await route.fetch();
		const m = await res.json();
		m.references.Kre99.artifacts.pdf = true;
		await route.fulfill({ json: m });
	});
	await page.goto('/master/main');
	await page.waitForSelector('.fragment mjx-container');
	await expect(page.locator('span.cite[data-target="Kre99-thm-2.1"] a').first()).toHaveAttribute(
		'href',
		/\/library\/Kre99\?page=4&result=Kre99-thm-2\.1$/
	);

	// with no copy filed there is no page to open, so the record is the best there is and the link goes to the node
	await page.unroute('**/build/manifest.json');
	await page.goto('/master/main');
	await page.waitForSelector('.fragment mjx-container');
	await expect(page.locator('span.cite[data-target="Kre99-thm-2.1"] a').first()).toHaveAttribute('href', /\/node\/Kre99-thm-2\.1$/);
});

test('a proposed text opens as source, and renders on asking', async ({ page }) => {
	// What is proposed is text to be written into a document, so the source is what a reader judges and the source is
	// what opens. The rendering is what it will look like afterwards, which is the second question. The control names
	// what a click gives rather than what is on screen.
	await page.goto('/node/sy-0004');
	await page.getByTestId('toggle-annotations').click();
	// the suggestion that proposes prose, not the citation suggestion beside it, which proposes a bibliography line
	const payload = page.locator('article.box[data-annotation-id="a-2026-09-16-0002"] [data-testid="payload"]');
	await expect(payload).toBeVisible();
	await expect(payload.getByTestId('payload-verbatim')).toContainText('\\ref{sy-0002}');
	await expect(payload.getByTestId('payload-rendered')).toHaveCount(0);
	const view = payload.getByTestId('payload-view');
	await expect(view).toHaveText('rendered latex');

	await view.click();
	await expect(payload.getByTestId('payload-verbatim')).toHaveCount(0);
	// rendered means rendered: the math is typeset, and the LaTeX that produced it is not on screen
	await expect(payload.getByTestId('payload-rendered').locator('mjx-container')).not.toHaveCount(0);
	await expect(payload.getByTestId('payload-rendered')).not.toContainText('\\ref');
	await expect(view).toHaveText('verbatim code');

	// copying is selecting the text, as it is everywhere else; the two buttons that did it are gone
	await expect(page.getByTestId('source-copy')).toHaveCount(0);
	await expect(page.getByTestId('source-copy-chat')).toHaveCount(0);
});
