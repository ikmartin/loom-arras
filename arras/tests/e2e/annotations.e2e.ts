// Annotations as a reader meets them: marks in the text, the margin's icons, the one popup, the stepper, the Comments and Notes lists, Quote, the toolbar's tools and format menu where a publisher serves writes, and Settings › Annotations. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { pane, settings, viewMenu } from '../workspace';
import { REFEREE, saying, serveKept } from '../manifest';

// these are about annotations and the page; the fixture's pending changes are left out, and tested apart (changes.e2e.ts)
test.beforeEach(({ page }) => serveKept(page));

/** A computed CSS colour's channels, in whichever form the browser serialises it: `rgb(r, g, b)`, `rgba(r, g, b, a)` or `color(srgb r g b / a)`. */
function channels(colour: string): { r: number; g: number; b: number; a: number } {
	const n = (colour.match(/[\d.]+(?:e-?\d+)?/g) ?? []).map(Number);
	if (colour.startsWith('color(')) return { r: Math.round(n[0] * 255), g: Math.round(n[1] * 255), b: Math.round(n[2] * 255), a: n[3] ?? 1 };
	return { r: n[0], g: n[1], b: n[2], a: n[3] ?? 1 };
}

/** One computed style property of an element. */
async function css(at: import('@playwright/test').Locator, prop: string): Promise<string> {
	return at.evaluate((el, p) => getComputedStyle(el).getPropertyValue(p), prop);
}

/** What a mark draws: its line's colour, thickness and height in the words, the band under them, and any outline. */
async function drawn(mark: import('@playwright/test').Locator): Promise<{ line: ReturnType<typeof channels>; bar: string; at: string; band: ReturnType<typeof channels>; outline: string }> {
	const cs = await mark.evaluate((el) => {
		const c = getComputedStyle(el);
		return { image: c.backgroundImage, size: c.backgroundSize, at: c.backgroundPositionY, band: c.backgroundColor, outline: c.outlineStyle };
	});
	return {
		line: channels(cs.image.match(/(?:rgba?|color)\([^)]*\)/)?.[0] ?? 'rgba(0, 0, 0, 0)'),
		bar: cs.size.split(' ')[1] ?? '',
		at: cs.at,
		band: channels(cs.band),
		outline: cs.outline
	};
}

/** Select an element's words as a reader would, and let go. */
async function selectWithin(at: import('@playwright/test').Locator): Promise<void> {
	await at.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
}

// The nine colours as theme.css draws them in the light: a line, and a band for a highlight.
const RED = { r: 204, g: 28, b: 28 };
const RED_BAND = { r: 255, g: 125, b: 115 };
const ORANGE_BAND = { r: 255, g: 190, b: 120 };
const BLUE = { r: 26, g: 111, b: 196 };
const BLUE_BAND = { r: 140, g: 205, b: 255 };
const GREEN = { r: 30, g: 125, b: 54 };
const GREY_BAND = { r: 216, g: 213, b: 205 };

// The mark is the annotation's own look: a highlight is its colour's band at its opacity, an underline or a strike a line of its weight, the marks of the one whose popup is open add what their style lacks, and a settled annotation is not drawn. Each test holds one clause of that rule against the computed style, never a pixel.
test.describe('marks', () => {
	const mark = (page: Page, id: string) => page.locator(`.fragment mark.annotation[data-annotation~="${id}"]`);

	test("a highlight is its colour's band at its opacity, with no line", async ({ page }) => {
		await page.goto('/master/drafting/main');
		const revision = mark(page, 'a-2026-09-16-ecnav2');
		await expect(revision).toHaveClass(/\bann-highlight\b/);
		const red = await drawn(revision);
		expect(red.band).toMatchObject(RED_BAND);
		expect(red.band.a).toBeCloseTo(0.65, 2);
		expect(red.bar).toBe('0px');
		const question = await drawn(mark(page, 'a-2026-09-16-bns3an'));
		expect(question.band).toMatchObject(BLUE_BAND);
		expect(question.band.a).toBeCloseTo(0.6, 2);
	});

	test('an underline is a line of its weight at the foot of the words, a strike one through them, each at its opacity', async ({ page }) => {
		await serveKept(page, (m) => {
			m.annotations['a-2026-09-16-bns3an'].look = { color: 'blue', style: 'underline', weight: 3, opacity: 100 };
			m.annotations['a-2026-09-16-ecnav2'].look = { color: 'green', style: 'strike', weight: 1, opacity: 50 };
		});
		await page.goto('/master/drafting/main');
		const under = mark(page, 'a-2026-09-16-bns3an');
		await expect(under).toHaveClass(/\bann-underline\b/);
		const u = await drawn(under);
		expect(u.line).toMatchObject({ ...BLUE, a: 1 });
		expect([u.bar, u.at]).toEqual(['3px', '100%']);
		expect(u.band.a).toBe(0);
		const struck = mark(page, 'a-2026-09-16-ecnav2');
		await expect(struck).toHaveClass(/\bann-strike\b/);
		const k = await drawn(struck);
		expect(k.line).toMatchObject(GREEN);
		expect(k.line.a).toBeCloseTo(0.5, 2);
		expect([k.bar, k.at]).toEqual(['1px', '58%']);
		expect(k.band.a).toBe(0);
	});

	test("the look is the annotation's own: renaming or deleting its type changes nothing drawn, and a colour the viewer does not know is grey", async ({ page }) => {
		await serveKept(page, (m) => {
			m.annotation_types = [];
			m.annotations['a-2026-09-16-bns3an'].look.color = 'teal';
		});
		await page.goto('/master/drafting/main');
		const revision = await drawn(mark(page, 'a-2026-09-16-ecnav2'));
		expect(revision.band).toMatchObject(RED_BAND);
		expect(revision.band.a).toBeCloseTo(0.65, 2);
		expect((await drawn(mark(page, 'a-2026-09-16-bns3an'))).band).toMatchObject(GREY_BAND);
	});

	test('the marks of the one annotation whose popup is open add what their style lacks: a line beneath a band, a band behind a line; nothing is outlined', async ({ page }) => {
		await serveKept(page, (m) => (m.annotations['a-2026-09-16-bns3an'].look = { color: 'blue', style: 'underline', weight: 2, opacity: 100 }));
		await page.goto('/master/drafting/main');
		const m = mark(page, 'a-2026-09-16-ecnav2');
		const other = mark(page, 'a-2026-09-16-bns3an');
		expect((await drawn(m)).bar).toBe('0px');
		expect((await drawn(other)).band.a).toBe(0);
		await m.click();
		await expect(m).toHaveClass(/\bopen\b/);
		await expect(page.getByTestId('ann-popup')).toHaveCount(1);
		const open = await drawn(m);
		expect([open.bar, open.at]).toEqual(['2px', '100%']);
		expect(open.line).toMatchObject(RED);
		expect(open.band).toMatchObject(RED_BAND);
		expect(open.outline).toBe('none');
		// the open mark says which popup is open, so the other stays as it was
		expect((await drawn(other)).band.a).toBe(0);
		await page.keyboard.press('Escape');
		await expect(m).not.toHaveClass(/\bopen\b/);
		expect((await drawn(m)).bar).toBe('0px');
		await other.click();
		await expect(other).toHaveClass(/\bopen\b/);
		const lined = await drawn(other);
		expect(lined.band).toMatchObject(BLUE_BAND);
		expect(lined.band.a).toBeCloseTo(0.35, 2);
		expect(lined.bar).toBe('2px');
	});

	test('an annotation with no mark of its own is a mark on its node\'s label, and several share one, which opens the first', async ({ page }) => {
		// a-2026-09-16-hqnbz4 has no quote and a-2026-09-16-a91hwf lost its anchor with no place loom could say its words were; both are put on sy-0002's label
		await serveKept(page, (m) => {
			m.annotations['a-2026-09-16-a91hwf'].target.key = 'sy-0002';
			m.annotations['a-2026-09-16-a91hwf'].version = null;
		});
		await page.goto('/master/drafting/main');
		const label = page.locator('.fragment .env[data-key="sy-0002"] > .env-label mark.annotation-label');
		await expect(label).toHaveCount(1);
		await expect(label).toHaveAttribute('data-annotation', 'a-2026-09-16-hqnbz4 a-2026-09-16-a91hwf');
		await expect(label).toContainText('Lemma');
		// no count is drawn anywhere: the label's own words are marked and nothing is added to them
		await expect(page.locator('.fragment button.comment-count')).toHaveCount(0);
		await label.click();
		await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', 'a-2026-09-16-hqnbz4');
		// the label's line has a count in the margin, and its chooser lists what starts there
		await page.getByTestId('margin-count').first().click();
		await expect(page.getByTestId('line-chooser').locator('.pkrow[data-annotation="a-2026-09-16-hqnbz4"]')).toHaveCount(1);
		await page.keyboard.press('Escape');
		// the label mark takes the look of its leading annotation, as any mark does
		await expect(label).toHaveClass(/\bann-highlight\b/);
		expect((await drawn(label)).band).toMatchObject(ORANGE_BAND);
	});

	test('a phrase with two annotations is one mark, opening the first, with no count drawn', async ({ page }) => {
		// the reply on the revision's phrase is made an annotation of its own, so the one mark carries two
		await serveKept(page, (m) => (m.annotations['a-2026-09-16-hwnav1'].in_reply_to = null));
		await page.goto('/node/sy-0003');
		const m = mark(page, 'a-2026-09-16-ecnav2');
		await expect(m).toHaveCount(1);
		await expect(m).toHaveAttribute('data-annotation', 'a-2026-09-16-ecnav2 a-2026-09-16-hwnav1');
		await expect(m).not.toHaveAttribute('data-count');
		expect(await m.evaluate((el) => getComputedStyle(el, '::after').content)).toBe('none');
		await m.click();
		await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', 'a-2026-09-16-ecnav2');
		// the margin has one for each, a count on their one line
		await expect(page.getByTestId('margin-count')).toHaveText('2');
	});

	test('a settled annotation is not drawn until settled annotations are shown, and then faintly, the words untouched', async ({ page }) => {
		// a-2026-09-16-hwtkaw is resolved
		await page.goto('/node/sy-0004');
		const m = mark(page, 'a-2026-09-16-hwtkaw');
		await expect(m).toHaveClass(/settled/);
		await expect(m).toContainText('disjoint union of orbits');
		expect((await drawn(m)).line.a).toBe(0);
		expect((await drawn(m)).band.a).toBe(0);
		await expect(m).toHaveAttribute('tabindex', '-1');
		// nothing to open: a click on the words is a click on the words
		await m.dispatchEvent('click');
		await expect(page.getByTestId('ann-popup')).toHaveCount(0);
		// shown by the toolbar's control: its look at 40% of its opacity, and the mark opens again
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		const shown = await drawn(m);
		expect(shown.band).toMatchObject(ORANGE_BAND);
		expect(shown.band.a).toBeCloseTo(0.24, 2);
		await m.click();
		await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', 'a-2026-09-16-hwtkaw');
	});

	test('a block mark is drawn in its look: a quote loom could not place marks its whole block, a list among them, underlined line by line', async ({ page }) => {
		// the publisher marks the block with `annotation-block` alone; the viewer gives it `annotation`, which every rule for the look, settled and hidden is keyed on
		await serveKept(page, (m) => (m.annotations['a-2026-09-16-ecnav2'].look = { color: 'red', style: 'underline', weight: 2, opacity: 100 }));
		await page.route('**/fragments/masters/drafting/main.html', async (route) => {
			const res = await route.fetch();
			const body = (await res.text()).replace('<ul data-src=', '<ul class="annotation-block" data-annotation="a-2026-09-16-ecnav2" data-src=');
			await route.fulfill({ response: res, body });
		});
		await page.goto('/master/drafting/main');
		const list = pane(page, 0).locator('.fragment ul.annotation-block');
		await expect(list).toHaveClass(/\bannotation\b/);
		await expect(list).toHaveClass(/\bann-underline\b/);
		const lined = await list.evaluate((el) => {
			const cs = getComputedStyle(el);
			return { decoration: cs.textDecorationLine, color: cs.textDecorationColor, thickness: cs.textDecorationThickness };
		});
		expect(lined.decoration).toBe('underline');
		expect(channels(lined.color)).toMatchObject({ ...RED, a: 1 });
		expect(lined.thickness).toBe('2px');
	});

	test('a displayed formula is ruled beneath for an underline and across for a strike, from the same variables', async ({ page }) => {
		// no fixture annotation marks a display, so the rule is held on the class and the look's variables alone: the same variables draw every shape
		await page.goto('/master/drafting/main');
		const vars = await mark(page, 'a-2026-09-16-ecnav2').evaluate((el) => {
			const probe = (style: string) => {
				const d = document.createElement('div');
				d.className = `math display annotation-block annotation ann-${style}`;
				d.style.cssText = '--ann-line: var(--ann-red); --ann-band: var(--ann-red-band); --ann-weight: 3px; --ann-opacity: 100%';
				el.closest('.fragment')!.append(d);
				const cs = getComputedStyle(d);
				const after = getComputedStyle(d, '::after');
				const out = { shadow: cs.boxShadow, decoration: cs.textDecorationLine, background: cs.backgroundColor, rule: after.borderTopWidth, ruled: after.content };
				d.remove();
				return out;
			};
			return { under: probe('underline'), strike: probe('strike') };
		});
		expect(vars.under.shadow).toMatch(/0px -3px 0px 0px inset/);
		expect(channels(vars.under.shadow)).toMatchObject(RED);
		expect(vars.under.decoration).toBe('none');
		expect(channels(vars.under.background).a).toBe(0);
		expect(vars.strike.shadow).toBe('none');
		expect(vars.strike.ruled).toBe('""');
		expect(vars.strike.rule).toBe('3px');
	});
});


/** Advertise `caps` from the publisher's write API, accept every write and keep each body by endpoint, the last one sent; `vite preview` serves none, and the controls appear only where one is. */
async function writes(page: Page, caps: string[] = ['annotate', 'reply', 'resolve', 'edit', 'delete', 'restore', 'types-save']): Promise<Record<string, Record<string, unknown>>> {
	const sent: Record<string, Record<string, unknown>> = {};
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
	await page.route('**/_api/*', (r) => {
		const endpoint = new URL(r.request().url()).pathname.split('/').pop() ?? '';
		sent[endpoint] = r.request().postDataJSON();
		return r.fulfill({ json: { ok: true, result: endpoint === 'annotate' ? 'a-2026-11-12-new000  sy-0003  untyped  (you)' : 'done', removed: [] } });
	});
	return sent;
}

const popup = (page: Page) => page.getByTestId('ann-popup');
const markOf = (page: Page, id: string) => page.locator(`.fragment mark.annotation[data-annotation~="${id}"]`);

/** Open the popup of annotation `id` from its first mark. */
async function openPopup(page: Page, id: string) {
	await markOf(page, id).first().click();
	const p = popup(page);
	await expect(p).toHaveAttribute('data-annotation-id', id);
	return p;
}

// The toolbar's two tools write where the reader is: Annotate marks words as they are selected, in the look in hand, and stays on; Comment leaves a comment at the next place clicked.
test.describe('the toolbar', () => {
	test('Annotate stays on, and words selected while it is on are marked at once in the look in hand, with Add comment at their end; Escape puts it down', async ({ page }) => {
		const sent = await writes(page);
		await page.goto('/node/sy-0003');
		const tool = page.getByTestId('tool-annotate');
		await tool.click();
		await expect(tool).toHaveAttribute('aria-pressed', 'true');
		await selectWithin(pane(page, 0).locator('.fragment .env[data-id="sy-0003"] > p[data-src]').first());
		await expect.poll(() => sent.annotate).toBeTruthy();
		// no type in hand, so the whole look travels and no type does; the place is the result the words are in
		expect(sent.annotate).toMatchObject({ target: 'sy-0003', look: { color: 'yellow', style: 'highlight', weight: 2, opacity: 60 } });
		expect(sent.annotate.quote).toContain('finite widget');
		expect(sent.annotate).not.toHaveProperty('type');
		expect(sent.annotate).not.toHaveProperty('message');
		await expect(page.getByTestId('add-comment')).toBeVisible();
		await expect(page.getByTestId('quote-offer')).toHaveCount(0);
		await expect(tool).toHaveAttribute('aria-pressed', 'true');
		await page.keyboard.press('Escape');
		await expect(tool).toHaveAttribute('aria-pressed', 'false');
	});

	test('a type that stays open asks something, so words marked with it open the popup to say it, and are written with what is said', async ({ page }) => {
		const sent = await writes(page);
		await page.addInitScript(() => localStorage.setItem('arras.annotate.hand', JSON.stringify({ type: 'question', over: {} })));
		await page.goto('/master/drafting/main');
		await page.getByTestId('tool-annotate').click();
		await selectWithin(pane(page, 0).locator('.fragment .env[data-id="sy-0003"] > p[data-src]').first());
		const draft = popup(page);
		await expect(draft).toBeVisible();
		await expect(draft.getByTestId('popup-type')).toContainText('Question');
		expect(sent.annotate).toBeUndefined();
		await draft.getByTestId('popup-comment-field').fill('Is finiteness needed?');
		await draft.getByTestId('popup-save').click();
		await expect.poll(() => sent.annotate).toBeTruthy();
		expect(sent.annotate).toMatchObject({ target: 'sy-0003', type: 'question', message: 'Is finiteness needed?', in: 'drafting/main.tex' });
		expect(sent.annotate).not.toHaveProperty('look');
	});

	test('Comment leaves a comment at the place clicked, on the result there, and goes off', async ({ page }) => {
		const sent = await writes(page);
		await page.goto('/master/drafting/main');
		const tool = page.getByTestId('tool-comment');
		await tool.click();
		await expect(tool).toHaveAttribute('aria-pressed', 'true');
		await pane(page, 0).locator('.fragment .env[data-id="sy-0003"] > p[data-src]').first().click({ position: { x: 4, y: 4 } });
		await expect(tool).toHaveAttribute('aria-pressed', 'false');
		const draft = popup(page);
		await expect(draft).toBeVisible();
		await draft.getByTestId('popup-comment-field').fill('Say where parity is used.');
		await expect(draft.getByTestId('popup-save')).toHaveText('Comment');
		await draft.getByTestId('popup-comment-field').press('Enter');
		await expect.poll(() => sent.annotate).toBeTruthy();
		expect(sent.annotate).toMatchObject({ target: 'sy-0003', message: 'Say where parity is used.', in: 'drafting/main.tex' });
		expect(sent.annotate).not.toHaveProperty('quote');
	});

	test('with no write API there are no tools and no verbs, and the popup still shows what is written', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await expect(page.getByTestId('step-next')).toBeVisible();
		await expect(page.getByTestId('tool-annotate')).toHaveCount(0);
		await expect(page.getByTestId('tool-comment')).toHaveCount(0);
		const p = await openPopup(page, 'a-2026-09-16-ecnav2');
		await expect(p.getByTestId('popup-comment')).toContainText('finite');
		await expect(p.getByTestId('popup-type')).toBeDisabled();
		await expect(p.getByTestId('popup-resolve')).toHaveCount(0);
		await expect(p.getByTestId('popup-delete')).toHaveCount(0);
		await expect(p.getByTestId('popup-reply')).toHaveCount(0);
	});
});

// The format menu sets the look in hand: the Type list, the look controls and Customize. The hand is remembered in this browser.
test.describe('the format menu', () => {
	test('lists No type and the quilt’s types with their keys; a type chosen, or a look, is what Annotate shows and what the next visit holds', async ({ page }) => {
		await writes(page);
		await page.goto('/master/drafting/main');
		const sample = page.getByTestId('tool-annotate').getByTestId('sample');
		await expect(sample).toHaveClass(/\bann-highlight\b/);
		await page.getByTestId('format-toggle').click();
		const menu = page.getByTestId('format-menu');
		await expect(menu.getByTestId('type-none')).toHaveAttribute('aria-selected', 'true');
		await expect(menu.getByTestId('type-row')).toHaveText(['Ab Revision 1', 'Ab Suggestion 2', 'Ab Question 3', 'Ab Note 4'].map((t) => new RegExp(t.replace(/ /g, '\\s*'))));
		await menu.locator('[data-testid="type-row"][data-type="revision"]').click();
		await expect(menu.locator('[data-testid="type-row"][data-type="revision"]')).toHaveAttribute('aria-selected', 'true');
		expect((await drawn(sample)).band).toMatchObject(RED_BAND);
		// a look over the type: strike, then green
		await menu.getByTestId('style-strike').click();
		await menu.getByTestId('swatch-green').click();
		await expect(sample).toHaveClass(/\bann-strike\b/);
		expect((await drawn(sample)).line).toMatchObject(GREEN);
		await page.keyboard.press('Escape');
		await expect(menu).toHaveCount(0);
		const kept = await page.evaluate(() => JSON.parse(localStorage.getItem('arras.annotate.hand') ?? '{}'));
		expect(kept).toEqual({ type: 'revision', over: { style: 'strike', color: 'green' } });
		await page.reload();
		await expect(page.getByTestId('tool-annotate').getByTestId('sample')).toHaveClass(/\bann-strike\b/);
	});

	test('while Annotate is on, a number key chooses a type and 0 none', async ({ page }) => {
		await writes(page);
		await page.goto('/master/drafting/main');
		await page.getByTestId('tool-annotate').click();
		await page.keyboard.press('3');
		await page.getByTestId('format-toggle').click();
		await expect(page.getByTestId('format-menu').locator('[data-testid="type-row"][data-type="question"]')).toHaveAttribute('aria-selected', 'true');
		await page.keyboard.press('Escape');
		await page.keyboard.press('0');
		await page.getByTestId('format-toggle').click();
		await expect(page.getByTestId('format-menu').getByTestId('type-none')).toHaveAttribute('aria-selected', 'true');
	});

	test('Customize opens Settings at Annotations', async ({ page }) => {
		await writes(page);
		await page.goto('/master/drafting/main');
		await page.getByTestId('format-toggle').click();
		await page.getByTestId('format-customize').click();
		await expect(page.getByTestId('settings-title')).toHaveText('Annotations');
		await expect(page.getByTestId('settings-annotations')).toBeVisible();
	});
});

// One popup for every annotation: its type and look, its comment edited in place, replies, Resolve where the type stays open, and Delete with its undo.
test.describe('the popup', () => {
	test('one at a time, at its mark; the mark of the open one closes it, and × and Escape do', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await openPopup(page, 'a-2026-09-16-bns3an');
		await openPopup(page, 'a-2026-09-16-ecnav2');
		await expect(popup(page)).toHaveCount(1);
		await markOf(page, 'a-2026-09-16-ecnav2').click();
		await expect(popup(page)).toHaveCount(0);
		await openPopup(page, 'a-2026-09-16-ecnav2');
		await popup(page).getByTestId('popup-close').click();
		await expect(popup(page)).toHaveCount(0);
		await openPopup(page, 'a-2026-09-16-ecnav2');
		await page.keyboard.press('Escape');
		await expect(popup(page)).toHaveCount(0);
		// hovering opens nothing
		await markOf(page, 'a-2026-09-16-ecnav2').hover();
		await expect(popup(page)).toHaveCount(0);
	});

	test('its type and its look change from its head: a type drops its own look, so it is drawn in the type’s, and a look changes only what it names', async ({ page }) => {
		const sent = await writes(page);
		await page.goto('/master/drafting/main');
		const p = await openPopup(page, 'a-2026-09-16-bns3an');
		await expect(p.getByTestId('popup-type')).toContainText('Question');
		await p.getByTestId('popup-type').click();
		const format = p.getByTestId('popup-format');
		await format.locator('[data-testid="type-row"][data-type="revision"]').click();
		await expect.poll(() => sent.edit).toBeTruthy();
		expect(sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', type: 'revision', look: null });
		// each write is answered before the next is taken
		await expect(format.getByTestId('type-none')).toBeEnabled();
		await format.getByTestId('swatch-green').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', look: { color: 'green' } });
		await expect(format.getByTestId('type-none')).toBeEnabled();
		await format.getByTestId('style-underline').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', look: { style: 'underline' } });
		await expect(format.getByTestId('type-none')).toBeEnabled();
		await format.getByTestId('type-none').click();
		await expect.poll(() => sent.edit).toMatchObject({ annotation: 'a-2026-09-16-bns3an', type: null, look: { color: 'blue', style: 'highlight' } });
	});

	test('the comment is edited in place, a reply is one line, and Resolve is offered only where the type stays open', async ({ page }) => {
		const sent = await writes(page);
		await serveKept(page, (m) => (m.annotations['a-2026-09-16-bns3an'].type = 'note'));
		await page.goto('/master/drafting/main');
		const p = await openPopup(page, 'a-2026-09-16-ecnav2');
		await p.getByTestId('popup-comment').click();
		const field = p.getByTestId('popup-comment-field');
		await field.fill('Say that finiteness is essential.');
		await p.getByTestId('popup-save').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-ecnav2', message: 'Say that finiteness is essential.' });
		await expect(p.getByTestId('popup-reply-row')).toHaveCount(1);
		await p.getByTestId('popup-reply').fill('Agreed.');
		await p.getByTestId('popup-reply').press('Enter');
		await expect.poll(() => sent.reply).toEqual({ annotation: 'a-2026-09-16-ecnav2', message: 'Agreed.' });
		await expect(p.getByTestId('popup-status')).toHaveText('Open');
		await p.getByTestId('popup-resolve').click();
		await expect.poll(() => sent.resolve).toEqual({ annotation: 'a-2026-09-16-ecnav2' });
		// a Note only informs: no Resolve and no status
		const note = await openPopup(page, 'a-2026-09-16-bns3an');
		await expect(note.getByTestId('popup-resolve')).toHaveCount(0);
		await expect(note.getByTestId('popup-status')).toHaveCount(0);
		await expect(note.getByTestId('popup-delete')).toBeVisible();
	});

	test('a resolved one offers Reopen, which is the undo of Resolve', async ({ page }) => {
		const sent = await writes(page);
		await page.goto('/node/sy-0004');
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		await page.keyboard.press('Escape');
		const p = await openPopup(page, 'a-2026-09-16-hwtkaw');
		await expect(p.getByTestId('popup-status')).toHaveText('Resolved');
		await p.getByTestId('popup-reopen').click();
		await expect.poll(() => sent.resolve).toEqual({ annotation: 'a-2026-09-16-hwtkaw', undo: true });
	});

	test('Delete asks nothing first; Undo at the foot of the window puts back what loom took out, and a refusal is said in the popup', async ({ page }) => {
		const removed = [{ event: 'created', id: 'a-2026-09-16-ecnav2' }];
		const sent: Record<string, Record<string, unknown>> = {};
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate', 'edit', 'delete', 'restore'], token: 't' } }));
		await page.route('**/_api/delete', (r) => ((sent.delete = r.request().postDataJSON()), r.fulfill({ json: { ok: true, result: 'deleted', removed } })));
		await page.route('**/_api/restore', (r) => ((sent.restore = r.request().postDataJSON()), r.fulfill({ json: { ok: true, result: 'restored' } })));
		await page.goto('/node/sy-0003');
		await (await openPopup(page, 'a-2026-09-16-ecnav2')).getByTestId('popup-delete').click();
		await expect.poll(() => sent.delete).toEqual({ annotation: 'a-2026-09-16-ecnav2' });
		const held = page.getByTestId('deleted');
		await expect(held).toContainText('Deleted Revision on Theorem 2.1.');
		await held.getByTestId('deleted-undo').click();
		await expect(held).toHaveCount(0);
		expect(sent.restore).toMatchObject({ events: removed });
		await page.unroute('**/_api/delete');
		await page.route('**/_api/delete', (r) => r.fulfill({ status: 400, json: { ok: false, error: { code: 'refused', message: 'an agent deletes only its own annotations' } } }));
		await page.reload();
		const p = await openPopup(page, 'a-2026-09-16-ecnav2');
		await p.getByTestId('popup-delete').click();
		await expect(p.getByTestId('popup-said')).toHaveText('an agent deletes only its own annotations');
		await expect(page.getByTestId('deleted')).toHaveCount(0);
	});
});

// What changes a look, and what a type is changed into: the line saying what a look was changed from, with Reset and Update, and Save as new type.
test.describe('changed from a type', () => {
	test('in the popup, a look that differs from its type says so; Reset drops it, and Update writes it into the type and drops it', async ({ page }) => {
		const sent = await writes(page);
		await serveKept(page, (m) => (m.annotations['a-2026-09-16-bns3an'].look = { color: 'green', style: 'highlight', weight: 2, opacity: 60 }));
		await page.goto('/master/drafting/main');
		const p = await openPopup(page, 'a-2026-09-16-bns3an');
		await p.getByTestId('popup-type').click();
		const line = p.getByTestId('modified-line');
		await expect(line).toContainText('Changed from Question');
		await line.getByTestId('modified-reset').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', look: null });
		delete sent.edit;
		await expect(line.getByTestId('modified-update')).toBeEnabled();
		await line.getByTestId('modified-update').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', look: null });
		const types = sent['types-save'].types as Record<string, unknown>[];
		expect(types.map((t) => t.id)).toEqual(['revision', 'suggestion', 'question', 'note']);
		expect(types[2]).toMatchObject({ id: 'question', name: 'Question', color: 'green', style: 'highlight', weight: 2, opacity: 60, open: true });
		expect(types[0]).toMatchObject({ color: 'red', opacity: 65 });
		// one whose look is its type's says nothing
		const same = await openPopup(page, 'a-2026-09-16-ecnav2');
		await same.getByTestId('popup-type').click();
		await expect(same.getByTestId('modified-line')).toHaveCount(0);
	});

	test('in the format menu, the look in hand over a type says so; Reset takes the type’s look, and Update writes the hand’s into the type', async ({ page }) => {
		const sent = await writes(page);
		await page.addInitScript(() => {
			if (!sessionStorage.getItem('seeded')) {
				localStorage.setItem('arras.annotate.hand', JSON.stringify({ type: 'revision', over: { color: 'blue' } }));
				sessionStorage.setItem('seeded', '1');
			}
		});
		await page.goto('/master/drafting/main');
		await page.getByTestId('format-toggle').click();
		const menu = page.getByTestId('format-menu');
		await expect(menu.getByTestId('modified-line')).toContainText('Changed from Revision');
		await menu.getByTestId('modified-reset').click();
		await expect(menu.getByTestId('modified-line')).toHaveCount(0);
		expect(await page.evaluate(() => JSON.parse(localStorage.getItem('arras.annotate.hand')!))).toEqual({ type: 'revision', over: {} });
		await menu.getByTestId('swatch-blue').click();
		await menu.getByTestId('modified-update').click();
		await expect.poll(() => sent['types-save']).toBeTruthy();
		expect((sent['types-save'].types as Record<string, unknown>[])[0]).toMatchObject({ id: 'revision', name: 'Revision', color: 'blue', style: 'highlight', opacity: 65 });
		await expect(menu.getByTestId('modified-line')).toHaveCount(0);
		expect(await page.evaluate(() => JSON.parse(localStorage.getItem('arras.annotate.hand')!))).toEqual({ type: 'revision', over: {} });
	});

	test('Save as new type starts a type in the look in hand, and once it is saved the hand holds it', async ({ page }) => {
		const sent = await writes(page);
		await page.route('**/_api/types-save', (r) => {
			sent['types-save'] = r.request().postDataJSON();
			const types = (sent['types-save'].types as { id?: string; name: string; color: string; style: string; weight: number; opacity: number }[]).map((t) => ({ id: t.id ?? 'hint', name: t.name, look: { color: t.color, style: t.style, weight: t.weight, opacity: t.opacity }, open: false, notes: false, instructions: '' }));
			return r.fulfill({ json: { ok: true, result: 'saved', types } });
		});
		await page.goto('/master/drafting/main');
		await page.getByTestId('format-toggle').click();
		await page.getByTestId('format-save-type').click();
		await expect(page.getByTestId('settings-title')).toHaveText('Annotations');
		const name = page.getByTestId('type-name');
		await expect(name).toBeFocused();
		await expect(page.getByTestId('type-tab')).toHaveCount(5);
		await name.fill('Hint');
		await page.getByTestId('types-save').click();
		await expect.poll(() => sent['types-save']).toBeTruthy();
		expect((sent['types-save'].types as Record<string, unknown>[]).at(-1)).toEqual({ name: 'Hint', color: 'yellow', style: 'highlight', weight: 2, opacity: 60, open: false, notes: false, instructions: '' });
		await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('arras.annotate.hand')!))).toEqual({ type: 'hint', over: {} });
	});
});

// Undo and Redo go back and forth over this page's own annotation writes; a delete stands at the foot of the window too.
test.describe('undo and redo', () => {
	/** Accept every write, as `writes` does, answering a delete with the events it took out. */
	async function undoable(page: Page) {
		const sent = await writes(page);
		const all: [string, Record<string, unknown>][] = [];
		await page.route('**/_api/*', (r) => {
			const endpoint = new URL(r.request().url()).pathname.split('/').pop() ?? '';
			const body = r.request().postDataJSON();
			sent[endpoint] = body;
			all.push([endpoint, body]);
			const result = endpoint === 'annotate' ? 'a-2026-11-12-new000  sy-0003  untyped  (you)' : endpoint === 'reply' ? 'a-2026-11-12-rep000  sy-0003  reply' : 'done';
			return r.fulfill({ json: { ok: true, result, removed: endpoint === 'delete' ? [{ event: 'created', id: body.annotation }] : [] } });
		});
		return { sent, all };
	}

	test('a new annotation is undone by deleting it and done again by restoring it, from the toolbar and the keys', async ({ page }) => {
		const { sent, all } = await undoable(page);
		await page.goto('/node/sy-0003');
		const undo = page.getByTestId('annotate-undo');
		const redo = page.getByTestId('annotate-redo');
		await expect(undo).toBeDisabled();
		await page.getByTestId('tool-annotate').click();
		await selectWithin(pane(page, 0).locator('.fragment .env[data-id="sy-0003"] > p[data-src]').first());
		await expect.poll(() => sent.annotate).toBeTruthy();
		await expect(undo).toBeEnabled();
		await expect(undo).toHaveAttribute('title', 'Undo new annotation (⌘Z)');
		await undo.click();
		await expect.poll(() => sent.delete).toEqual({ annotation: 'a-2026-11-12-new000' });
		await expect(undo).toBeDisabled();
		await redo.click();
		await expect.poll(() => sent.restore).toEqual({ events: [{ event: 'created', id: 'a-2026-11-12-new000' }] });
		// and the keys do the same, once the last step is answered
		await expect(undo).toBeEnabled();
		await page.keyboard.press('Escape');
		await pane(page, 0).locator('.fragment').first().focus();
		await page.keyboard.press('ControlOrMeta+z');
		await expect.poll(() => all.filter(([e]) => e === 'delete').length).toBe(2);
		await expect(redo).toBeEnabled();
		await page.keyboard.press('ControlOrMeta+Shift+z');
		await expect.poll(() => all.filter(([e]) => e === 'restore').length).toBe(2);
	});

	test('an edit is undone by an edit back to the words, the type and the look it had', async ({ page }) => {
		const { sent } = await undoable(page);
		await page.goto('/master/drafting/main');
		const p = await openPopup(page, 'a-2026-09-16-bns3an');
		await p.getByTestId('popup-comment').click();
		await p.getByTestId('popup-comment-field').fill('Is a fixed point one orbit?');
		await p.getByTestId('popup-save').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', message: 'Is a fixed point one orbit?' });
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', message: 'Is the orbit of a fixed point counted as one point or two?' });
		await page.getByTestId('annotate-redo').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', message: 'Is a fixed point one orbit?' });
		// a type changed and changed back: it had the question's own look, so the undo drops what the edit set
		await p.getByTestId('popup-type').click();
		await p.getByTestId('popup-format').locator('[data-testid="type-row"][data-type="revision"]').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', type: 'revision', look: null });
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => sent.edit).toEqual({ annotation: 'a-2026-09-16-bns3an', type: 'question', look: null });
	});

	test('a resolve is undone by reopening, and a delete by restoring what loom took out, the same act as the Undo at the foot of the window', async ({ page }) => {
		const { sent, all } = await undoable(page);
		await page.goto('/node/sy-0003');
		const p = await openPopup(page, 'a-2026-09-16-ecnav2');
		await p.getByTestId('popup-resolve').click();
		await expect.poll(() => sent.resolve).toEqual({ annotation: 'a-2026-09-16-ecnav2' });
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => sent.resolve).toEqual({ annotation: 'a-2026-09-16-ecnav2', undo: true });
		await expect(p.getByTestId('popup-delete')).toBeEnabled();
		await p.getByTestId('popup-delete').click();
		await expect.poll(() => sent.delete).toEqual({ annotation: 'a-2026-09-16-ecnav2' });
		const held = page.getByTestId('deleted');
		await expect(held).toHaveCount(1);
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => sent.restore).toEqual({ events: [{ event: 'created', id: 'a-2026-09-16-ecnav2' }] });
		await expect(held).toHaveCount(0);
		await page.getByTestId('annotate-redo').click();
		await expect.poll(() => all.filter(([e]) => e === 'delete').length).toBe(2);
		await expect(held).toHaveCount(1);
		// the foot of the window's Undo is the same step
		await held.getByTestId('deleted-undo').click();
		await expect.poll(() => all.filter(([e]) => e === 'restore').length).toBe(2);
		await expect(held).toHaveCount(0);
		await expect(page.getByTestId('annotate-redo')).toBeEnabled();
	});

	test('the annotation open is removed by Delete or Backspace, with the same undo', async ({ page }) => {
		const { sent, all } = await undoable(page);
		await page.goto('/master/drafting/main');
		await openPopup(page, 'a-2026-09-16-ecnav2');
		await expect(page.getByTestId('annotate-hint')).toContainText('Delete removes it');
		await page.keyboard.press('Delete');
		await expect.poll(() => sent.delete).toEqual({ annotation: 'a-2026-09-16-ecnav2' });
		await expect(popup(page)).toHaveCount(0);
		await expect(page.getByTestId('deleted')).toContainText('Deleted Revision on Theorem 2.1.');
		await page.getByTestId('annotate-undo').click();
		await expect.poll(() => sent.restore).toBeTruthy();
		await openPopup(page, 'a-2026-09-16-bns3an');
		await page.keyboard.press('Backspace');
		await expect.poll(() => all.filter(([e]) => e === 'delete').map(([, b]) => b.annotation)).toEqual(['a-2026-09-16-ecnav2', 'a-2026-09-16-bns3an']);
		// nothing open, nothing deleted
		await page.keyboard.press('Delete');
		await page.waitForTimeout(300);
		expect(all.filter(([e]) => e === 'delete')).toHaveLength(2);
	});
});

// The hint under the toolbar says what the tool in hand does.
test.describe('the hint', () => {
	test('says what Annotate and Comment do while they are on, and goes when they are put down', async ({ page }) => {
		await writes(page);
		await page.addInitScript(() => localStorage.setItem('arras.annotate.hand', JSON.stringify({ type: 'question', over: {} })));
		await page.goto('/master/drafting/main');
		const hint = page.getByTestId('annotate-hint');
		await expect(hint).toHaveCount(0);
		await page.getByTestId('tool-annotate').click();
		await expect(hint).toHaveText('Annotate is on. Select text to mark it as Question. Number keys switch type, 0 for none. Esc stops.');
		await page.keyboard.press('0');
		await expect(hint).toHaveText('Annotate is on. Select text to mark it. Number keys switch type, 0 for none. Esc stops.');
		await page.getByTestId('tool-comment').click();
		await expect(hint).toHaveText('Comment is on. Click where the comment should go. Esc stops.');
		await page.keyboard.press('Escape');
		await expect(hint).toHaveCount(0);
	});

	test('is not drawn where nothing can be written', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await openPopup(page, 'a-2026-09-16-ecnav2');
		await expect(page.getByTestId('annotate-hint')).toHaveCount(0);
	});
});

// "Written on earlier words": an annotation whose words are gone shows the words it was written on and opens the version that holds them, and is reached from where its words were.
test.describe('written on earlier words', () => {
	// on the fixture as it stands: sy-0001 has a pending change, so its block is the publisher's merged one, which carries the gone mark as the document's does
	test.beforeEach(({ page }) => page.unroute('**/build/manifest.json'));

	test('its gone mark stands where its words were, opens its popup with the words as they were, and the version opens with its annotations drawn', async ({ page }) => {
		await page.goto('/node/sy-0001');
		const gone = page.locator('.fragment mark.annotation.gone[data-annotation="a-2026-09-16-a91hwf"]');
		await expect(gone).toHaveCount(1);
		await expect(gone).toHaveText('');
		// the margin has its icon, a speech bubble since it says something
		const icon = page.locator('[data-testid="margin-icon"][data-annotation="a-2026-09-16-a91hwf"]');
		await expect(icon).toHaveClass(/\btalk\b/);
		await gone.click();
		const p = popup(page);
		await expect(p).toHaveAttribute('data-annotation-id', 'a-2026-09-16-a91hwf');
		await expect(p.getByTestId('popup-earlier')).toContainText('Written on earlier words');
		await expect(p.getByTestId('popup-earlier')).toContainText('an involution');
		await p.getByTestId('earlier-open').click();
		const version = p.getByTestId('version-view');
		await expect(version).toContainText('Definition');
		const was = version.locator('mark.annotation[data-annotation~="a-2026-09-16-a91hwf"]');
		await expect(was).toHaveClass(/\bopen\b/);
		await expect(was).toContainText('involution');
		expect((await drawn(was)).band).toMatchObject(BLUE_BAND);
		await p.getByTestId('earlier-open').click();
		await expect(version).toHaveCount(0);
	});

	test('a mark in the version opens that annotation’s popup in place of this one', async ({ page }) => {
		// the version marks every annotation written on it; a second one is put in by the test, since the fixture's version holds one
		await page.route('**/fragments/versions/fb425ed10ccf378e.html', async (route) => {
			const res = await route.fetch();
			const body = (await res.text()).replace('is a pair', 'is a <mark class="annotation" data-annotation="a-2026-09-16-ecnav2">pair</mark>');
			await route.fulfill({ response: res, body });
		});
		await page.goto('/node/sy-0001');
		await page.locator('.fragment mark.annotation.gone[data-annotation="a-2026-09-16-a91hwf"]').click();
		await popup(page).getByTestId('earlier-open').click();
		const version = popup(page).getByTestId('version-view');
		// its own mark opens nothing new
		await version.locator('mark.annotation[data-annotation~="a-2026-09-16-a91hwf"]').click();
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-a91hwf');
		const other = version.locator('mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]');
		expect((await drawn(other)).band).toMatchObject(RED_BAND);
		await other.click();
		await expect(popup(page)).toHaveCount(1);
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-ecnav2');
		await expect(popup(page)).toBeInViewport();
	});

	test('an annotation whose words still stand says nothing of earlier words', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await expect((await openPopup(page, 'a-2026-09-16-ecnav2')).getByTestId('popup-earlier')).toHaveCount(0);
	});
});

// The margin: one icon per annotation on the line its first mark stands on, a count where several start on one line, which opens the line chooser.
test.describe('the margin', () => {
	test('one icon per annotation drawn, a speech bubble where it says something; an icon opens its popup', async ({ page }) => {
		await serveKept(page, (m) => (m.annotations['a-2026-09-16-ecnav2'].body_html = ''));
		await page.goto('/master/drafting/main');
		const icon = page.locator('[data-testid="margin-icon"][data-annotation="a-2026-09-16-ecnav2"]');
		await expect(icon).toHaveCount(1);
		await expect(icon).not.toHaveClass(/\btalk\b/);
		await expect(page.locator('[data-testid="margin-icon"][data-annotation="a-2026-09-16-a91hwf"]')).toHaveClass(/\btalk\b/);
		// a settled one is not drawn at rest, so it has no icon
		await expect(page.locator('[data-testid="margin-icon"][data-annotation="a-2026-09-16-hwtkaw"]')).toHaveCount(0);
		await icon.click();
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-ecnav2');
		await expect(icon).toHaveClass(/\bon\b/);
		// level with its mark
		// the margin is drawn again as the layout settles, so an icon read between two drawings has no box yet
		const middle = async (at: import('@playwright/test').Locator) => at.evaluate((el) => {
			const r = el.getClientRects()[0];
			return r ? r.top + r.height / 2 : NaN;
		});
		await expect.poll(async () => Math.abs((await middle(icon)) - (await middle(markOf(page, 'a-2026-09-16-ecnav2')))) < 10).toBe(true);
	});

	test('where several start on one line, a count opens the line chooser, which opens the one picked', async ({ page }) => {
		await page.goto('/master/drafting/main');
		// the lemma's label carries the untyped suggestion, and its words the question
		const count = page.getByTestId('margin-count');
		await expect(count).toHaveText('2');
		await count.click();
		const chooser = page.getByTestId('line-chooser');
		const rows = chooser.locator('.pkrow');
		await expect(rows).toHaveCount(2);
		await expect(chooser.locator('.pkrow[data-annotation="a-2026-09-16-bns3an"]')).toContainText('Question · The synthetic quilt');
		await chooser.locator('.pkrow[data-annotation="a-2026-09-16-bns3an"]').click();
		await expect(chooser).toHaveCount(0);
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-bns3an');
	});
});

// The stepper goes through the annotations in reading order, from the toolbar's arrows or J and K.
test.describe('the stepper', () => {
	test('J and K open the next and the previous in reading order, round the ends, and the count says where', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await expect(page.getByTestId('step-count')).toHaveText('5 annotations');
		await pane(page, 0).locator('.fragment p').first().click();
		await page.keyboard.press('j');
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-a91hwf');
		await expect(page.getByTestId('step-count')).toHaveText('1 of 5');
		await page.keyboard.press('j');
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-hqnbz4');
		await page.keyboard.press('j');
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-bns3an');
		await page.keyboard.press('k');
		await expect(page.getByTestId('step-count')).toHaveText('2 of 5');
		await page.getByTestId('step-next').click();
		await page.getByTestId('step-next').click();
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-ecnav2');
		// the last is on the whole document and has no mark: it is shown in the list instead
		await page.getByTestId('step-next').click();
		await expect(page.getByTestId('step-count')).toHaveText('5 of 5');
		await expect(page.locator('[data-testid="comment-card"][data-annotation="a-2026-09-16-6sn46y"]')).toHaveClass(/\bon\b/);
		await page.getByTestId('step-next').click();
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-a91hwf');
		// K from the first goes round to the last
		await page.getByTestId('step-prev').click();
		await expect(page.getByTestId('step-count')).toHaveText('5 of 5');
	});
});

// Comments: every annotation here in reading order, a card each; To do and the filter narrow it, and the text with it.
test.describe('the Comments list', () => {
	test('a card per annotation in reading order, with its colour, author, words and comment; a card opens its annotation at its mark', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await expect(page.getByTestId('open-comments')).toContainText('5');
		await page.getByTestId('open-comments').click();
		const cards = page.getByTestId('comment-card');
		await expect(cards).toHaveCount(5);
		expect(await cards.evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.annotation))).toEqual(['a-2026-09-16-a91hwf', 'a-2026-09-16-hqnbz4', 'a-2026-09-16-bns3an', 'a-2026-09-16-ecnav2', 'a-2026-09-16-6sn46y']);
		const revision = page.locator('[data-testid="comment-card"][data-annotation="a-2026-09-16-ecnav2"]');
		await expect(revision).toContainText('agent');
		await expect(revision).toContainText('Revision');
		await expect(revision).toContainText('finite widget');
		await expect(revision).toContainText('1 reply');
		await revision.click();
		await expect(popup(page)).toHaveAttribute('data-annotation-id', 'a-2026-09-16-ecnav2');
		await expect(revision).toHaveClass(/\bon\b/);
		await page.getByTestId('side-close').click();
		await expect(page.getByTestId('side-list')).toHaveCount(0);
	});

	test('To do keeps the open annotations of types that stay open from others than the reader, and the text with it', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await page.getByTestId('open-comments').click();
		const todo = page.getByTestId('comments-todo');
		await expect(todo).toContainText('3');
		await todo.click();
		await expect(todo).toHaveAttribute('aria-pressed', 'true');
		expect(await page.getByTestId('comment-card').evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.annotation))).toEqual(['a-2026-09-16-hqnbz4', 'a-2026-09-16-ecnav2', 'a-2026-09-16-6sn46y']);
		// the reader's own question is left out of the text too
		await expect(markOf(page, 'a-2026-09-16-bns3an')).toHaveClass(/\bhidden\b/);
		await expect(page.getByTestId('step-count')).toHaveText('3 annotations');
		await todo.click();
		await expect(markOf(page, 'a-2026-09-16-bns3an')).not.toHaveClass(/\bhidden\b/);
	});

	test('the filter leaves out a person, here and in the text, and shows the resolved', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await page.getByTestId('open-comments').click();
		await page.getByTestId('comments-filter').click();
		const who = page.getByTestId('filter-who');
		await expect(who).toHaveCount(2);
		await expect(page.getByTestId('filter-menu')).toContainText('The synthetic quilt (you)');
		await page.locator('[data-testid="filter-who"][data-author="agent"]').uncheck();
		await expect(page.getByTestId('comment-card')).toHaveCount(2);
		await expect(markOf(page, 'a-2026-09-16-ecnav2')).toHaveClass(/\bhidden\b/);
		await page.locator('[data-testid="filter-who"][data-author="agent"]').check();
		await expect(page.getByTestId('comment-card')).toHaveCount(5);
		await page.getByTestId('filter-resolved').check();
		await expect(page.locator('[data-testid="comment-card"][data-annotation="a-2026-09-16-hwtkaw"]')).toHaveClass(/\bsettled\b/);
		await expect(page.locator('.fragment').first()).toHaveClass(/show-settled/);
	});
});

// Notes: every annotation whose type is listed in Notes, from every document, grouped by document, each linking back to its place.
test.describe('the Notes list', () => {
	test('holds the annotations of types listed in Notes, grouped by document, and a card goes back to its place with its popup open', async ({ page }) => {
		await serveKept(page, (m) => {
			m.annotations['a-2026-09-16-ecnav2'].type = 'note';
			m.annotations['a-2026-09-16-xgtcve'].type = 'note';
		});
		await page.goto('/node/sy-0001');
		await expect(page.getByTestId('open-notes')).toContainText('2');
		await page.getByTestId('open-notes').click();
		await expect(page.getByTestId('notes-group')).toHaveText([/main\.tex\s*1/, /talk\.tex\s*1/]);
		const card = page.locator('[data-testid="note-card"][data-annotation="a-2026-09-16-ecnav2"]');
		await expect(card).toHaveAttribute('href', 'quilt:a-2026-09-16-ecnav2');
		await expect(card).toContainText('finite widget');
		await card.click();
		await expect(page.locator('[data-testid="ann-popup"][data-annotation-id="a-2026-09-16-ecnav2"]')).toBeVisible();
	});

	test('with no type listed in Notes it says how one gets there', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await page.getByTestId('open-notes').click();
		await expect(page.getByTestId('side-list')).toContainText('No notes yet');
	});
});

// Quote: a bare selection, no tool on, offers Quote, which copies the words and where they came from, and writes nothing.
test.describe('Quote', () => {
	test('copies the words and a link to their place, says so, and writes nothing', async ({ page }) => {
		const sent = await writes(page);
		await page.addInitScript(() => {
			(window as unknown as { copied: string[] }).copied = [];
			Object.defineProperty(navigator, 'clipboard', { value: { writeText: async (t: string) => void (window as unknown as { copied: string[] }).copied.push(t) }, configurable: true });
		});
		await page.goto('/master/drafting/main');
		// Quote stands at the end of the words, so they are scrolled to as a reader would have them on screen
		await markOf(page, 'a-2026-09-16-ecnav2').scrollIntoViewIfNeeded();
		await selectWithin(markOf(page, 'a-2026-09-16-ecnav2'));
		await page.getByTestId('quote-offer').click();
		const toast = page.getByTestId('toast');
		await expect(toast).toContainText('Quoted for your agent');
		await expect(toast).toContainText('“finite widget”');
		const copied = await page.evaluate(() => (window as unknown as { copied: string[] }).copied);
		expect(copied).toEqual(['> finite widget\n— [main.tex, Theorem 2.1](quilt:drafting/main.tex#sy-0003)']);
		await expect(page.getByTestId('quote-offer')).toHaveCount(0);
		expect(Object.keys(sent)).toEqual([]);
	});

	test('is offered without a publisher, since it writes nothing', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await selectWithin(markOf(page, 'a-2026-09-16-ecnav2'));
		await expect(page.getByTestId('quote-offer')).toBeVisible();
	});
});

// Settings › Annotations: one type at a time, a draft until Save, which writes the types file whole through `types-save`.
test.describe('Settings › Annotations', () => {
	test('a renamed type and a deleted one are saved together; deleting one a mode uses asks first', async ({ page }) => {
		const sent = await writes(page);
		await page.goto('/master/drafting/main');
		await settings(page, 'annotations');
		const tabs = page.getByTestId('type-tab');
		await expect(tabs).toHaveCount(4);
		await tabs.nth(1).click();
		await expect(page.getByTestId('type-name')).toHaveValue('Suggestion');
		await expect(page.getByTestId('type-modes')).toHaveText('Used by the audit, referee and review modes.');
		await page.getByTestId('type-name').fill('Idea');
		await expect(tabs.nth(1)).toContainText('Idea');
		await tabs.nth(2).click();
		await page.getByTestId('type-delete').click();
		const warn = page.getByTestId('type-delete-warn');
		await expect(warn).toContainText('The audit and referee modes use this type');
		await page.getByTestId('type-delete-yes').click();
		await expect(tabs).toHaveCount(3);
		await page.getByTestId('types-save').click();
		await expect.poll(() => sent['types-save']).toBeTruthy();
		const saved = sent['types-save'].types as { id: string; name: string; open: boolean; color: string }[];
		expect(saved.map((t) => [t.id, t.name])).toEqual([
			['revision', 'Revision'],
			['suggestion', 'Idea'],
			['note', 'Note']
		]);
		expect(saved[0]).toEqual({ id: 'revision', name: 'Revision', color: 'red', style: 'highlight', weight: 2, opacity: 65, open: true, notes: false, instructions: expect.stringContaining('wrong') });
	});

	test('a new type is written with no id, and Restore defaults writes the defaults', async ({ page }) => {
		const sent = await writes(page);
		await page.goto('/master/drafting/main');
		await settings(page, 'annotations');
		await page.getByTestId('types-add').click();
		await expect(page.getByTestId('type-name')).toBeFocused();
		await page.getByTestId('type-name').fill('Hint');
		await page.getByTestId('type-notes').check();
		await page.getByTestId('type-open-true').check();
		await page.getByTestId('types-save').click();
		await expect.poll(() => sent['types-save']).toBeTruthy();
		const saved = sent['types-save'].types as Record<string, unknown>[];
		expect(saved.at(-1)).toEqual({ name: 'Hint', color: 'green', style: 'highlight', weight: 2, opacity: 50, open: true, notes: true, instructions: '' });
		await page.getByTestId('types-defaults').click();
		await expect.poll(() => sent['types-save']).toEqual({ defaults: true });
	});

	test('without a publisher that saves types it is shown as published', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await settings(page, 'annotations');
		await expect(page.getByTestId('settings-read-only')).toContainText('.loom/annotation-types.toml');
		await expect(page.getByTestId('type-name')).toBeDisabled();
		await expect(page.getByTestId('types-add')).toHaveCount(0);
	});
});

test.describe('the settled control', () => {
	const settledMark = (page: Page) => page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-hwtkaw"]');

	/** The control, read where it stands: under *view*, which is opened to read it. */
	async function settled(page: Page) {
		await viewMenu(page);
		return page.getByTestId('toggle-settled');
	}

	/** Close the menu with Escape, which leaves the page as it was. */
	const shut = (page: Page) => page.keyboard.press('Escape');

	test('on a document it shows and hides the settled marks, and their popups open only while it is on', async ({ page }) => {
		await page.goto('/master/drafting/main');
		const m = settledMark(page);
		await expect(m).toHaveClass(/settled/);
		expect((await drawn(m)).band.a).toBe(0);
		const control = await settled(page);
		await expect(control).toHaveText(/^show settled annotations/);
		await expect(control).toHaveAttribute('aria-checked', 'false');
		await control.click();
		await expect(await settled(page)).toHaveText(/^hide settled annotations/);
		await expect(control).toHaveAttribute('aria-checked', 'true');
		await shut(page);
		await expect(page.getByTestId('toolbar-view-on')).toBeVisible();
		await expect(page.locator('.fragment').first()).toHaveClass(/show-settled/);
		expect((await drawn(m)).band).toMatchObject(ORANGE_BAND);
		expect((await drawn(m)).band.a).toBeCloseTo(0.24, 2);
		// the resolved suggestion on the theorem has no quote, so shown it is a mark on the theorem's label
		await expect(page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-tc3rcf"]')).toHaveCount(1);
		await m.click();
		await expect(page.getByTestId('ann-popup')).toHaveAttribute('data-annotation-id', 'a-2026-09-16-hwtkaw');
		await page.keyboard.press('Escape');
		await (await settled(page)).click();
		await expect(await settled(page)).toHaveText(/^show settled annotations/);
		await shut(page);
		expect((await drawn(m)).band.a).toBe(0);
		await expect(page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-tc3rcf"]')).toHaveCount(0);
	});

	test('on a node the same control, and the s key', async ({ page }) => {
		await page.goto('/node/sy-0004');
		const m = settledMark(page);
		expect((await drawn(m)).band.a).toBe(0);
		await (await settled(page)).click();
		await expect(await settled(page)).toHaveText(/^hide settled annotations/);
		await shut(page);
		expect((await drawn(m)).band.a).toBeCloseTo(0.24, 2);
		// the key, from inside the document, flips it back and forth
		await page.locator('.fragment').first().focus();
		await page.keyboard.press('s');
		expect((await drawn(m)).band.a).toBe(0);
		await expect(await settled(page)).toHaveText(/^show settled annotations/);
		await shut(page);
		await page.locator('.fragment').first().focus();
		await page.keyboard.press('s');
		expect((await drawn(m)).band.a).toBeCloseTo(0.24, 2);
		await expect(await settled(page)).toHaveText(/^hide settled annotations/);
	});

	test('the keys draw no focus ring around the document', async ({ page }) => {
		// a click focuses the document without a ring and a key then asks for one, which around a document taller than the window showed as two blue rules down its sides
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment mjx-container');
		const fragment = page.locator('.fragment');
		await fragment.locator('p').first().click();
		await page.keyboard.press('s');
		expect(await fragment.evaluate((el) => el.matches(':focus-visible'))).toBe(true);
		await expect(fragment).toHaveCSS('outline-style', 'none');
	});

	test('it is off again on a fresh visit', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await (await settled(page)).click();
		await expect(await settled(page)).toHaveText(/^hide settled annotations/);
		await page.goto('/master/drafting/main');
		await expect(await settled(page)).toHaveText(/^show settled annotations/);
		expect((await drawn(settledMark(page))).band.a).toBe(0);
	});

	test('a link to a settled annotation turns it on and opens its popup, one with no quote included', async ({ page }) => {
		// a message or the Context links a settled annotation by `quilt:`; following it is a request to see it, so the control comes on for the sitting and the popup opens, rather than the reader landing on a page where nothing is drawn
		await saying(page, '<p>See <a href="quilt:a-2026-09-16-hwtkaw"></a>.</p>');
		await page.goto(`/session/${REFEREE}`);
		await page.getByTestId('message-1').locator('a[href="quilt:a-2026-09-16-hwtkaw"]').click();
		await expect(page.getByTestId('toolbar-view-on')).toBeVisible();
		await expect(page.locator('[data-pane="1"] [data-testid="ann-popup"][data-annotation-id="a-2026-09-16-hwtkaw"]')).toBeVisible();
		// a resolved annotation with no quote is a label mark only while settled annotations are drawn, and its popup opens from it and says it was resolved
		await page.goto('/node/sy-0003');
		const label = page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-tc3rcf"]');
		await expect(label).toHaveCount(0);
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		await shut(page);
		await label.click();
		const p = page.getByTestId('ann-popup');
		await expect(p).toHaveAttribute('data-annotation-id', 'a-2026-09-16-tc3rcf');
		await expect(p.getByTestId('popup-status')).toHaveText('Resolved');
	});
});
