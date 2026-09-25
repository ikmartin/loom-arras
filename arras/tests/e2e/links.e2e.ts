// Links: one form for what the quilt owns, `quilt:`, beside `cited:` and the citations a document makes, and one rule for where every link opens: revealed where it is already open, otherwise a new tab in the pane the reader is not in. An empty link is named by the viewer, and resting on a link previews what it names. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { beside, pane } from '../workspace';
import { REFEREE, saying, serve } from '../manifest';

test.describe('naming', () => {
	test('an empty link reads as the viewer names the thing; a titled one as written', async ({ page }) => {
		await saying(page, '<p><a href="quilt:sy-0003"></a>, <a href="quilt:sy-0003">the parity theorem</a>, <a href="quilt:a-2026-09-16-0001"></a> and <a href="quilt:drafting/main.tex"></a>.</p>');
		await page.goto('/session/' + REFEREE);
		const links = page.getByTestId('message-1').locator('a');
		await expect(links.nth(0)).toHaveText('Theorem 2.1');
		await expect(links.nth(1)).toHaveText('the parity theorem');
		await expect(links.nth(2)).toHaveText('objection on Theorem 2.1');
		await expect(links.nth(3)).toHaveText('main.tex');
	});
});

test.describe('the one rule', () => {
	test('what is open is revealed where it is, its place marked, and no tab is added', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:drafting/main.tex#sy-0003"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toHaveClass(/travelled/);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toBeInViewport();
	});

	test('what is not open opens as a new tab in the other pane, and the Chat stays', async ({ page }) => {
		// sy-999A is in the talk only, so the open main.tex does not hold it
		await saying(page, '<p>See <a href="quilt:sy-999A"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(2);
		await expect(pane(page, 0).getByRole('tab', { selected: true })).toContainText('sy-999A');
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('a node an open document holds is revealed in the document, not opened beside it (DR-280-ikmartin)', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:sy-0003"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toHaveClass(/travelled/);
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toBeInViewport();
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('behind another tab, the document is brought forward to the node', async ({ page }) => {
		await saying(page, '<p>See <a href="quilt:sy-0003"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await expect(pane(page, 0).locator('.fragment').first()).toBeVisible();
		// put main.tex behind the talk, opened from the side panel into the reader's pane
		await pane(page, 0).getByRole('tab').first().click();
		await page.getByTestId('docs-drafts').getByRole('link', { name: 'talk.tex' }).click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(2);
		await expect(pane(page, 0).getByRole('tab', { selected: true })).toContainText('talk.tex');
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		await expect(pane(page, 0).getByRole('tab', { selected: true })).toContainText('main.tex');
		await expect(pane(page, 0).locator('[id="sy-0003"]')).toBeInViewport();
	});

	test("a document's link to its own content takes the same path: it scrolls there and marks it", async ({ page }) => {
		await page.goto('/master/main');
		const ref = pane(page, 0).locator('.fragment a.ref[href^="#"]').first();
		await expect(ref).toBeVisible();
		const id = decodeURIComponent((await ref.getAttribute('href'))!.slice(1));
		await ref.click();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).locator(`[id="${id}"]`)).toHaveClass(/travelled/);
		await expect(pane(page, 0).locator(`[id="${id}"]`)).toBeInViewport();
	});

	test('a link to an annotation opens what it is on, with its box open', async ({ page }) => {
		await saying(page, '<p>My <a href="quilt:a-2026-09-16-0001"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await pane(page, 1).getByTestId('message-1').locator('a').click();
		const box = pane(page, 0).getByTestId('comment-expanded');
		await expect(box).toBeVisible();
		await expect(box.locator('[data-annotation-id="a-2026-09-16-0001"]')).toHaveCount(1);
		await expect.poll(() => new URL(page.url()).searchParams.get('note')).toBe('a-2026-09-16-0001');
	});

	test("a context's link follows the one rule: a new tab in the other pane, the node it came from kept behind it", async ({ page }) => {
		// sy-0005's context links sy-0002, which the pane holding sy-0005 does not show
		await page.goto('/node/sy-0005' + beside('/context/sy-0005'));
		const link = pane(page, 1).getByTestId('context').locator('a[href*="/node/sy-0002"]').first();
		await link.click();
		// the context stays where it was; the other pane gains a tab, and the node the context is about is still there
		await expect(pane(page, 1).getByTestId('context')).toBeVisible();
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(2);
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect.poll(() => new URL(page.url()).pathname).toBe('/node/sy-0002');
	});
});

test.describe('cited works', () => {
	test('a citation with no digest result behind it links to its reference', async ({ page }) => {
		await page.goto('/master/main');
		const cite = page.locator('.fragment span.cite[data-citekey="Har77"]').first();
		await expect(cite.locator('a')).toHaveAttribute('href', '/library/Har77');
	});

	test('a citation opens the cited paper at the result, not the digest node', async ({ page }) => {
		// `[1, Theorem 2.1]` names a theorem in a paper, so where a copy is filed the link goes to the paper at that result; the digest node's page is loom's record of it, a thing to go and look at and not what the citation names
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container');
		await expect(page.locator('span.cite[data-target="Kre99-thm-2.1"] a').first()).toHaveAttribute('href', /\/library\/Kre99\?page=4&result=Kre99-thm-2\.1$/);

		// with no copy filed there is no page to open, so the record is the best there is and the link goes to the node
		await page.unroute('**/build/manifest.json');
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container');
		await expect(page.locator('span.cite[data-target="Kre99-thm-2.1"] a').first()).toHaveAttribute('href', /\/node\/Kre99-thm-2\.1$/);
	});

	test('a link to a result of a cited work opens the paper at its page, as a citation of it does', async ({ page }) => {
		await serve(page, (m) => (m.references.Kre99.artifacts.pdf = true));
		await saying(page, '<p>See <a href="quilt:Kre99-thm-2.1"></a>.</p>');
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		const link = pane(page, 1).getByTestId('message-1').locator('a');
		await expect(link).toHaveText('Kre99 · Thm 2.1');
		await link.click();
		await expect.poll(() => new URL(page.url()).pathname).toBe('/library/Kre99');
		await expect.poll(() => new URL(page.url()).searchParams.get('page')).toBe('4');
	});
});

test.describe('previews', () => {
	test('a quilt: link previews what it names, and a link to an annotation previews what it is on', async ({ page }) => {
		await saying(page, '<p><a href="quilt:sy-0003"></a> and <a href="quilt:a-2026-09-16-0001"></a>.</p>');
		await page.goto('/session/' + REFEREE);
		const links = page.getByTestId('message-1').locator('a');
		await links.nth(0).hover();
		await expect(page.getByTestId('link-preview')).toBeVisible();
		await expect(page.getByTestId('link-preview')).toContainText('widget');
		await page.mouse.move(0, 0);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
		await links.nth(1).hover();
		await expect(page.getByTestId('link-preview')).toBeVisible();
		await expect(page.getByTestId('link-preview').locator('.env[data-id="sy-0003"]').first()).toBeVisible();
	});

	test('resting on a link to a node shows its statement, and Escape dismisses it', async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const link = page.getByTestId('context').getByRole('link', { name: /^Definition/ }).first();
		await link.hover();
		const card = page.getByTestId('link-preview');
		await expect(card).toBeVisible();
		await expect(card.locator('.fragment mjx-container').first()).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(card).toHaveCount(0);
	});

	test('a quick pass over a link shows nothing', async ({ page }) => {
		// the card's delay runs on the page's clock, so the test moves that clock past it rather than sleeping
		await page.clock.install();
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const link = page.getByTestId('context').locator('a[href^="/node/sy-"]').first();
		await link.hover();
		await page.mouse.move(900, 600);
		await page.clock.runFor(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
		// and the same link rested on does show one, so the absence above is the pass being quick
		await link.hover();
		await page.clock.runFor(500);
		await expect(page.getByTestId('link-preview')).toBeVisible();
	});

	test('a link to a kind with no preview opens no card', async ({ page }) => {
		// a document, a context or a session has no small render: nothing is made up in its place (P3)
		// the card's delay runs on the page's clock, which the test moves past it rather than sleeping
		await page.clock.install();
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		// a node link in the same context does preview, so the absence below is the kind's and not the card's
		await page.getByTestId('context').getByRole('link', { name: /^Definition/ }).first().hover();
		await page.clock.runFor(600);
		await expect(page.getByTestId('link-preview')).toBeVisible();
		await page.keyboard.press('Escape');
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
		const doc = page.getByTestId('context').getByRole('link', { name: 'main.tex' }).first();
		await doc.hover();
		await page.clock.runFor(600);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
	});

	test('a citation previews the page at the place it names, and nothing where the place is unknown', async ({ page }) => {
		// a hover over a citation shows the paper, not a card about it: the entry and the digest are what the work's own Info view is for; with no copy on this machine there is no page to show, so nothing opens
		// the card's delay runs on the page's clock, so each absence below is asserted after moving that clock past it
		await page.clock.install();
		await page.goto('/master/main');
		await page.waitForSelector('.fragment mjx-container'); // typesetting reflows the text, which would move the link out from under the pointer
		await page.locator('.fragment span.cite[data-citekey="Har77"] a').first().hover();
		await page.clock.runFor(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);

		await serve(page, (m) => {
			m.references.Har77.artifacts.pdf = true;
			m.references.Kre99.artifacts.pdf = true;
		});
		await page.reload();
		await page.waitForSelector('.fragment mjx-container');

		// a postnote names a place, so a copy being filed is not on its own a reason to open one: `[Har77, Chapter II]` knows no page, and the front page of Hartshorne is not Chapter II
		await page.locator('.fragment span.cite[data-citekey="Har77"] a').first().hover();
		await page.clock.runFor(500);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);

		// where the postnote carries its own page, that is the place, and the card is the page and nothing else
		await page.goto('/node/Kre99-thm-2.1');
		await page.waitForSelector('.fragment mjx-container');
		await page.locator('.fragment span.cite[data-postnote="Theorem 2.1, p.~4"] a').first().hover();
		await expect(page.getByTestId('preview-page')).toBeVisible();
		// the card is the paper, not text about it; its one line is the `open here` every card carries, and the renderer's own load notice is not text about the work
		await expect(page.getByTestId('link-preview').locator('p:not(.opens):not(.problem)')).toHaveCount(0);
	});
});
