// Review: document-scoped tables of recorded states, the causes a stale key opens beside its document, what an incoming pull changes, and the guided review of what needs a decision. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { serve } from '../manifest';

test.describe('the views', () => {
	test('the default document opens first and the corpus-wide views follow the document tabs', async ({ page }) => {
		await page.goto('/review?show=stale');
		const tabs = page.getByRole('navigation', { name: 'Review views' });
		await expect(tabs.getByRole('link')).toHaveText(['main.tex', 'talk.tex', /Needs Review \(\d+\)/, /Incoming \(\d+\)/]);
		await expect(tabs.getByRole('link', { name: 'main.tex' })).toHaveAttribute('aria-current', 'page');
		await expect(page.locator('main table.list')).toBeVisible();
		await expect(page.getByTestId('filter-show')).toHaveCount(0);
	});

	test('the blockers address lands on the default document', async ({ page }) => {
		await page.goto('/blockers');
		await expect(page).toHaveURL(/\/review$/);
		await expect(page.getByRole('navigation', { name: 'Review views' }).getByRole('link', { name: 'main.tex' })).toHaveAttribute('aria-current', 'page');
	});

	test('the review panel explains itself and names the command behind each state, and its help closes on a press outside it', async ({ page }) => {
		await page.goto('/review');
		await expect(page.locator('p.lead')).toContainText('Recorded states are read from this corpus’s review history.');
		await page.getByTestId('help-review').click();
		const help = page.getByTestId('help-panel-review');
		await expect(help).toContainText('stale');
		await expect(help).toContainText('accept');
		await page.mouse.click(900, 700);
		await expect(help).toHaveCount(0);
	});
});

test.describe('recorded states', () => {
	test('review statement badges agree with proved and settled counts', async ({ page }) => {
		await serve(page, (m) => {
			m.nodes['sy-0003'].derived = { proved: true, settled: true };
			m.nodes['sy-0002'].derived = { proved: true, settled: false };
			m.keys['sy-0002'].acceptance.fresh = true;
		});
		await page.goto('/review');
		await expect(page.getByTestId('review-counts')).toContainText('2 proved');
		await expect(page.getByTestId('review-counts')).toContainText('1 settled');
		await expect(page.locator('#review-sy-0003 .badge .chip')).toHaveText(['accepted', 'proved', 'settled']);
		await expect(page.locator('#review-sy-0002 .badge .chip')).toHaveText(['accepted', 'proved']);
	});

	test('rows and counts follow the selected document while a shared block keeps one state', async ({ page }) => {
		await page.goto('/review');
		const tabs = page.getByRole('navigation', { name: 'Review views' });
		await expect(page.locator('#review-sy-0003')).toBeVisible();
		await expect(page.locator('#review-sy-999a')).toHaveCount(0);
		await expect(page.locator('#review-sy-0002')).toBeVisible();
		await expect(page.locator('#review-sy-999b')).toContainText('conflicted');
		const mainCounts = await page.getByTestId('review-counts').innerText();

		await tabs.getByRole('link', { name: 'talk.tex' }).click();
		await expect(page).toHaveURL(/\/review\?document=drafting%2Ftalk\.tex$/);
		await expect(page.locator('#review-sy-999a')).toBeVisible();
		await expect(page.locator('#review-sy-0003')).toHaveCount(0);
		await expect(page.locator('#review-sy-0002')).toBeVisible();
		await expect(page.locator('#review-sy-999b')).toContainText('conflicted');
		await expect(page.getByTestId('review-counts')).not.toHaveText(mainCounts);
		await expect(page.getByText('Sessions')).toHaveCount(0);
		await expect(page.getByText('Undigested citations')).toHaveCount(0);

		await page.goto('/review?document=drafting%2Fmissing.tex');
		await expect(page.getByRole('navigation', { name: 'Review views' }).getByRole('link', { name: 'main.tex' })).toHaveAttribute('aria-current', 'page');
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
			return { documentRight: document.right, comparisonLeft: comparison.left, pageWidth: window.document.documentElement.scrollWidth, windowWidth: window.innerWidth };
		});
		expect(comparisonLayout.comparisonLeft).toBeGreaterThan(comparisonLayout.documentRight);
		expect(comparisonLayout.pageWidth).toBeLessThanOrEqual(comparisonLayout.windowWidth);
		await page.goto('/review');
		const dependent = page.locator('table.list tr', { hasText: 'sy-0002' }).first();
		await dependent.getByRole('link', { name: 'sy-0001', exact: true }).click();
		await expect(page).toHaveURL(/#cite-nodes-sy-0002-tex-185-sy-0001-eq-fix$/);
		await expect(page.locator('#cite-nodes-sy-0002-tex-185-sy-0001-eq-fix')).toHaveClass(/review-citation-target/);
		await expect(page.getByTestId('review-comparison')).toContainText('involution');
	});
});

test.describe('incoming and guided review', () => {
	test('incoming review stays separate from recorded states and opens a document comparison', async ({ page }) => {
		let incorporated: Record<string, string> | null = null;
		await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['sync-incorporate'] } }));
		await page.route('**/_api/sync-incorporate', async (route) => {
			incorporated = route.request().postDataJSON();
			await route.fulfill({ json: { ok: true, result: { source_commit: 'c'.repeat(40), sync_commit: 'd'.repeat(40), integrated: 'b'.repeat(40), paths: ['drafting/main.tex'] } } });
		});
		await serve(page, (m) => {
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
		});
		await page.goto('/review?show=incoming');
		await expect(page.getByTestId('incoming-sy-0003')).toBeVisible();
		await expect(page.getByRole('navigation', { name: 'Review views' }).getByRole('link', { name: 'Incoming (1)' })).toBeVisible();
		await expect(page.getByTestId('review-counts')).toHaveCount(0);
		await expect(page.getByTestId('incoming-incorporation')).toContainText('neither push nor accept mathematics');
		const files = page.getByRole('heading', { name: 'Changed source files' }).locator('xpath=following-sibling::ul[1]');
		await expect(files).toContainText('drafting/main.tex');
		await expect(files).toContainText('references.bib');
		// in document order, the incorporation stands before the change it incorporates
		const order = await page.locator('[data-testid="incoming-incorporation"], [data-testid="incoming-sy-0003"]').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.testid));
		expect(order).toEqual(['incoming-incorporation', 'incoming-sy-0003']);
		await page.getByRole('button', { name: 'Incorporate pull' }).click();
		await expect.poll(() => incorporated).toEqual({ incoming: 'b'.repeat(40), base: 'a'.repeat(40) });
		await page.getByText('references.bib', { exact: true }).last().click();
		await expect(page.locator('.incoming-file-diff')).toContainText('A collaborator reference');
		await page.getByTestId('incoming-sy-0003').locator('h2 a').click();
		await expect(page).toHaveURL(/incoming=sy-0003/);
		await expect(page.getByTestId('incoming-comparison')).toBeVisible();
	});

	test('Needs review separates the block queue, pending OK, and attention', async ({ page }) => {
		await serve(page, (m) => {
			m.unresolved = [
				{ key: 'sy-0001', status: 'needs-review', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: true, local_changed: false, invalidated: false },
				{ key: 'sy-0002', status: 'ok', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: false, invalidated: false },
				{ key: 'sy-0003', status: 'requires-attention', cause: 'earlier-change', pull: '', changed_text: false, invalidated: false }
			];
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
		await serve(page, (m) => {
			m.unresolved = [
				{ key: 'sy-0002', status: 'needs-review', cause: 'incoming-pull', pull: 'b'.repeat(40), changed_text: false, local_changed: true, invalidated: false },
				{ key: 'sy-0003', status: 'needs-review', cause: 'earlier-change', pull: '', changed_text: false, local_changed: true, invalidated: false }
			];
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
});
