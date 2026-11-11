// Annotations as a reader meets them: marks in the text, the boxes they open floating or inline, all of them opened at once, what a suggestion proposes, and the verbs and tools that write one where a publisher serves. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, prefs, settings, viewMenu } from '../workspace';
import { openPicker, pickSession } from '../picker';
import { manifest, QUICK, REFEREE, serve } from '../manifest';

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
const ORANGE = { r: 196, g: 90, b: 10 };
const ORANGE_BAND = { r: 255, g: 190, b: 120 };
const BLUE = { r: 26, g: 111, b: 196 };
const BLUE_BAND = { r: 140, g: 205, b: 255 };
const GREEN = { r: 30, g: 125, b: 54 };
const GREY_BAND = { r: 216, g: 213, b: 205 };
const NEUTRAL = { r: 111, g: 109, b: 102 };

// The mark is the annotation's own look: a highlight is its colour's band at its opacity, an underline or a strike a line of its weight, the mark whose box is open adds what its style lacks, and a settled annotation is not drawn. Each test holds one clause of that rule against the computed style, never a pixel.
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
		await serve(page, (m) => {
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
		await serve(page, (m) => {
			m.annotation_types = [];
			m.annotations['a-2026-09-16-bns3an'].look.color = 'teal';
		});
		await page.goto('/master/drafting/main');
		const revision = await drawn(mark(page, 'a-2026-09-16-ecnav2'));
		expect(revision.band).toMatchObject(RED_BAND);
		expect(revision.band.a).toBeCloseTo(0.65, 2);
		expect((await drawn(mark(page, 'a-2026-09-16-bns3an'))).band).toMatchObject(GREY_BAND);
	});

	test('the one mark whose box is open adds what its style lacks: a line beneath a band, a band behind a line; nothing is outlined', async ({ page }) => {
		await serve(page, (m) => (m.annotations['a-2026-09-16-bns3an'].look = { color: 'blue', style: 'underline', weight: 2, opacity: 100 }));
		await page.goto('/master/drafting/main');
		const m = mark(page, 'a-2026-09-16-ecnav2');
		const other = mark(page, 'a-2026-09-16-bns3an');
		expect((await drawn(m)).bar).toBe('0px');
		expect((await drawn(other)).band.a).toBe(0);
		await m.click();
		await expect(m).toHaveClass(/\bopen\b/);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(1);
		const open = await drawn(m);
		expect([open.bar, open.at]).toEqual(['2px', '100%']);
		expect(open.line).toMatchObject(RED);
		expect(open.band).toMatchObject(RED_BAND);
		expect(open.outline).toBe('none');
		// the open mark says which box is open, so the other stays as it was
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

	test('an annotation with no mark of its own is a mark on its node\'s label, and several share one', async ({ page }) => {
		// a-2026-09-16-hqnbz4 has no quote and a-2026-09-16-a91hwf lost its anchor; both are put on sy-0002's label
		await serve(page, (m) => (m.annotations['a-2026-09-16-a91hwf'].target.key = 'sy-0002'));
		await page.goto('/master/drafting/main');
		const label = page.locator('.fragment .env[data-key="sy-0002"] > .env-label mark.annotation-label');
		await expect(label).toHaveCount(1);
		await expect(label).toHaveAttribute('data-annotation', 'a-2026-09-16-hqnbz4 a-2026-09-16-a91hwf');
		await expect(label).toContainText('Lemma');
		// no count is drawn anywhere: the label's own words are marked and nothing is added to them
		await expect(page.locator('.fragment button.comment-count')).toHaveCount(0);
		await label.click();
		const boxes = page.locator('aside.comment-slot.expanded article.box');
		await expect(boxes).toHaveCount(2);
		await expect(page.locator('aside.comment-slot.expanded article.box[data-annotation-id="a-2026-09-16-hqnbz4"]')).toHaveCount(1);
		// the label mark takes the look of its leading annotation, as any mark does
		await expect(label).toHaveClass(/\bann-highlight\b/);
		expect((await drawn(label)).band).toMatchObject(ORANGE_BAND);
	});

	test('a phrase with two annotations is one mark whose box lists both, with no count drawn', async ({ page }) => {
		// the reply on the revision's phrase is made an annotation of its own, so the one mark carries two
		await serve(page, (m) => (m.annotations['a-2026-09-16-hwnav1'].in_reply_to = null));
		await page.goto('/node/sy-0003');
		const m = mark(page, 'a-2026-09-16-ecnav2');
		await expect(m).toHaveCount(1);
		await expect(m).toHaveAttribute('data-annotation', 'a-2026-09-16-ecnav2 a-2026-09-16-hwnav1');
		await expect(m).not.toHaveAttribute('data-count');
		expect(await m.evaluate((el) => getComputedStyle(el, '::after').content)).toBe('none');
		await m.click();
		await expect(page.locator('aside.comment-slot.expanded article.box')).toHaveCount(2);
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
		// nothing to open: a click on the words is a click on the words, and show all opens nothing
		await m.dispatchEvent('click');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		await viewMenu(page);
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		await viewMenu(page);
		await page.getByTestId('toggle-annotations').click();
		// shown by the toolbar's control: its look at 40% of its opacity, and the mark opens again
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		const shown = await drawn(m);
		expect(shown.band).toMatchObject(ORANGE_BAND);
		expect(shown.band.a).toBeCloseTo(0.24, 2);
		await m.click();
		await expect(page.locator('aside.comment-slot.expanded article.box[data-annotation-id="a-2026-09-16-hwtkaw"]')).toHaveCount(1);
	});

	test('the session filter hides marks, not only counts', async ({ page }) => {
		// the question is moved into the closed session, which the view hides at rest
		await serve(page, (m) => (m.annotations['a-2026-09-16-bns3an'].run = QUICK));
		await page.goto('/master/drafting/main');
		const m = mark(page, 'a-2026-09-16-bns3an');
		await expect(m).toHaveClass(/hidden/);
		await expect(m).toContainText('one or two points');
		expect((await drawn(m)).band.a).toBe(0);
		await m.dispatchEvent('click');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		// the revision, in the open session, is drawn as before
		await expect(mark(page, 'a-2026-09-16-ecnav2')).not.toHaveClass(/hidden/);
		// admitting closed sessions draws it
		await openPicker(page);
		await page.getByTestId('show-closed').click();
		await page.getByTestId('closed-yes').click();
		await page.keyboard.press('Escape');
		await expect(m).not.toHaveClass(/hidden/);
		expect((await drawn(m)).band).toMatchObject(BLUE_BAND);
		expect((await drawn(m)).band.a).toBeCloseTo(0.6, 2);
		await m.click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(1);
	});

	test('a block mark is drawn in its look: a quote loom could not place marks its whole block, a list among them, underlined line by line', async ({ page }) => {
		// the publisher marks the block with `annotation-block` alone; the viewer gives it `annotation`, which every rule for the look, settled and hidden is keyed on
		await serve(page, (m) => (m.annotations['a-2026-09-16-ecnav2'].look = { color: 'red', style: 'underline', weight: 2, opacity: 100 }));
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

test.describe('marks and boxes', () => {
	test('a node draws no annotation list: its marks open their boxes, and show all opens every one that is drawn, in the flow', async ({ page }) => {
		// a mark opens its annotation as a floating box over the text; `show all annotations` opens every one; nothing below the node lists them again
		await page.goto('/node/sy-0003');
		// counted as "every open annotation on this key has a box", not as a literal, so adding one to the fixture does not fail a test that is about marks and boxes agreeing; a settled one is not drawn and so not opened
		const open = await page.evaluate(async () => {
			const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
			// every key the node owns: its statement and its proofs, which carry ids of their own rather than a `/proof` suffix
			const keys = Object.entries(m.keys)
				.filter(([, k]: [string, any]) => k.node === 'sy-0003')
				.map(([id]) => id);
			return Object.values(m.annotations).filter((a: any) => keys.includes(a.target.key) && !a.in_reply_to && a.status === 'open' && !a.in).length;
		});
		expect(open).toBeGreaterThan(0);
		await expect(page.getByTestId('annotation-list')).toHaveCount(0);
		// the marks that are drawn: the revision's, and not the resolved suggestion's on the proof
		const marks = page.locator('.fragment mark.annotation:not(.settled)');
		await expect(marks).toHaveCount(open);
		await expect(page.locator('.fragment mark.annotation.settled')).toHaveCount(1);
		await marks.first().click();
		const opened = page.locator('[data-testid="comment-expanded"] article.box');
		await expect(opened).toHaveCount(1);
		await expect(opened.locator('header')).toHaveCount(0); // the box begins with the body
		await expect(opened.locator('article.reply')).toHaveCount(1);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
		// the toolbar's show all opens every one at once, each at its mark or beside its result's label, in the flow rather than floating
		await viewMenu(page);
		await page.getByTestId('toggle-annotations').click();
		await expect(opened).toHaveCount(open);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(0);
		await viewMenu(page);
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		// and with them closed, a single mark still floats
		await marks.first().click();
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
	});

	test('floating, a mark opens a box clear of every edge and a second mark a second box; × closes one, Escape or a click away the rest, and hovering opens nothing', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		// any delay a hover could open a box after runs on the page's clock, which the test moves on rather than sleeping
		await page.clock.install();
		await page.goto('/master/drafting/main');
		// a fragment is wired once for the default placement and again when the stored preferences arrive, so waiting on the marks is not enough: wait until it is wired for the placement under test
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mark.annotation[data-wired-mark]');
		const first = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]');
		const second = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-bns3an"]');
		const slots = page.locator('aside.comment-slot.floating');
		const open = page.locator('.comment-slot.expanded.floating');
		await expect(slots).toHaveCount(0);

		// hovering never opens one: a box the pointer summons cannot be read without holding it still, and moving toward the box leaves the mark
		await first.hover({ force: true });
		await page.clock.runFor(400);
		await expect(slots).toHaveCount(0);

		await first.click();
		await expect(slots).toHaveCount(1);
		// it floats over the page rather than opening in the flow, so it is free to overlap the text and the gutter
		await expect(slots).toHaveCSS('position', 'fixed');
		await expect(slots.locator('article.box')).toHaveCount(1);
		// and it is kept clear of every edge, so a mark near one slides the box rather than clipping it
		const inset = await slots.evaluate((el) => {
			const r = el.getBoundingClientRect();
			return Math.min(r.left, r.top, window.innerWidth - r.right, window.innerHeight - r.bottom);
		});
		expect(inset).toBeGreaterThanOrEqual(3.5);

		// a second mark opens a second box rather than replacing the first, so two annotations can be read side by side
		await second.click();
		await expect(open).toHaveCount(2);
		// a box's own × closes just that one
		await open.first().locator('.comment-close').click();
		await expect(open).toHaveCount(1);
		// clicking the text closes what is left, leaving no faded stub behind
		await page.locator('.fragment p').first().click({ position: { x: 4, y: 4 } });
		await expect(open).toHaveCount(0);
		await expect(page.locator('.comment-slot.floating.behind')).toHaveCount(0);

		// Escape closes the front-most, and a click anywhere away closes what is open
		await first.click();
		await expect(slots).toHaveCount(1);
		await page.keyboard.press('Escape');
		await expect(slots).toHaveCount(0);
		await first.click();
		await expect(slots).toHaveCount(1);
		await page.mouse.click(4, 4);
		await expect(slots).toHaveCount(0);
	});

	test('floating, a box that grows as its content renders stays clear of the window foot', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mark.annotation[data-wired-mark]');
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]');
		// the mark mid-window, so a box grown past the window fits neither below it nor above it and is held at the foot, where nothing is left to scroll to reach it
		await mark.evaluate((el) => el.scrollIntoView({ block: 'center' }));
		await mark.click();
		const slot = page.locator('aside.comment-slot.floating');
		await expect(slot).toHaveCount(1);
		// what renders after the box is placed makes it taller, as math and a proposed theorem do
		await slot.evaluate((el) => {
			const grown = document.createElement('div');
			grown.style.height = '2000px';
			el.querySelector('article.box')!.append(grown);
		});
		await expect
			.poll(() => slot.evaluate((el) => window.innerHeight - el.getBoundingClientRect().bottom))
			.toBeGreaterThanOrEqual(3.5);
	});

	test('inline, a mark expands its comment beneath its paragraph; clicking away closes it', async ({ page }) => {
		await prefs(page, { comments: 'inline' });
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);

		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]');
		await mark.click();
		const open = page.locator('aside.comment-slot.expanded');
		await expect(open).toHaveCount(1);
		await expect(open.locator('article.box')).toHaveCount(1); // the reply is inside its parent, not a second box
		await expect(open.locator('.replies')).toBeVisible();
		await expect(mark).toHaveAttribute('aria-expanded', 'true');
		// in the flow, directly after the paragraph holding the mark
		const follows = await mark.evaluate((m) => {
			const block = m.closest('p, li, .math.display, .annotation-block, summary');
			return block?.nextElementSibling?.className ?? '(nothing follows the block)';
		});
		expect(follows.split(/\s+/)).toContain('expanded');

		// clicking away closes it, leaving nothing behind
		await page.mouse.click(5, 5);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);

		// and Escape closes the front-most
		await mark.click();
		await expect(open).toHaveCount(1);
		await page.keyboard.press('Escape');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
	});

	test('inline, a mark on a label opens its box beneath the label', async ({ page }) => {
		await prefs(page, { comments: 'inline' });
		await page.goto('/master/drafting/main');
		// a-2026-09-16-a91hwf lost its anchor, so it is marked on sy-0001's label
		const label = page.locator('.fragment .env[data-key="sy-0001"] > .env-label mark.annotation-label');
		await expect(label).toHaveAttribute('data-annotation', 'a-2026-09-16-a91hwf');
		await label.click();
		const open = page.locator('aside.comment-slot.expanded');
		await expect(open.locator('article.box')).toHaveCount(1);
		expect(await label.evaluate((m) => m.closest('.env-label')?.nextElementSibling?.className ?? '')).toContain('expanded');
	});

	test('e opens every annotation at its mark, and h closes them', async ({ page }) => {
		// the document view draws no buttons for these, so the keys are the whole affordance here
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment mjx-container');
		const boxes = page.locator('aside.comment-slot.expanded');
		await expect(page.getByTestId('content-head')).toHaveCount(0);
		await expect(boxes).toHaveCount(0);

		await page.locator('.fragment').focus();
		await page.keyboard.press('e');
		await expect.poll(() => boxes.count()).toBeGreaterThan(1);

		await page.keyboard.press('h');
		await expect(boxes).toHaveCount(0);
	});

	test('the keys draw no focus ring around the document', async ({ page }) => {
		// a click focuses the document without a ring and a key then asks for one, which around a document taller than the window showed as two blue rules down its sides
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment mjx-container');
		const fragment = page.locator('.fragment');
		await fragment.locator('p').first().click();
		await page.keyboard.press('e');
		expect(await fragment.evaluate((el) => el.matches(':focus-visible'))).toBe(true);
		await expect(fragment).toHaveCSS('outline-style', 'none');
	});

	test('a document carries annotations of its own, and they are read beside it', async ({ page }) => {
		// a remark about the whole paper is not drawn above its title; it is read in what the session did, beside the document
		await page.goto('/master/drafting/main' + beside(`/session/${REFEREE}?view=did`));
		await expect(page.getByTestId('document-annotations')).toHaveCount(0);
		const did = page.getByTestId('session-did');
		// found by its id rather than by being first; the list is compact rows, not boxes
		const own = Object.values(manifest.annotations as Record<string, { id: string; body_html: string; target: { key: string } }>).find(
			(a) => a.body_html.includes('which conventions it inherits') && a.target.key === 'drafting/main.tex'
		)!;
		await expect(did.locator(`[id="ann-${own.id}"]`)).toHaveCount(1);
	});
});

// The box begins with the body (annotation study fixes 12–17): nothing is said in words that the record already shows, the annotation's colour is the stripe, what it proposes stands at a rule in that colour, and everything an annotation can do happens inside its box.
test.describe('the box', () => {
	/** Advertise `caps` from the publisher's write API and accept every write. */
	async function writes(page: Page, caps: string[]): Promise<void> {
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
		await page.route('**/_api/*', (r) => r.fulfill({ json: { ok: true, result: 'done' } }));
	}

	/** Open the box of the annotation `id` from its mark, floating over the node it is on. */
	async function openBox(page: Page, path: string, id: string) {
		await page.goto(path);
		await page.locator(`.fragment .annotation[data-annotation~="${id}"]`).first().click();
		const box = page.locator(`[data-testid="comment-expanded"] article.box[data-annotation-id="${id}"]`);
		await expect(box).toBeVisible();
		return box;
	}

	test('a reply being written survives a new manifest: the box is made again with its text, open, the cursor where it was', async ({ page }) => {
		// a serving publisher writes a new manifest whenever the quilt changes, an agent's annotation among them, and the document re-draws its boxes: a reply kept only in the box was lost with it
		let revision = 0;
		let served = 0;
		await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['reply', 'resolve', 'edit', 'delete'] } }));
		await serve(page, (m) => {
			served += 1;
			m.sessions[0].title = `A sitting, revision ${revision}`;
		});
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		await box.getByTestId('verb-reply').click();
		const text = box.getByTestId('verb-text');
		await text.fill('Half of what I meant to say');
		revision = 1;
		const before = served;
		await expect.poll(() => served).toBeGreaterThan(before + 1);
		await page.waitForTimeout(500);
		const again = page.locator('[data-testid="comment-expanded"] article.box[data-annotation-id="a-2026-09-16-ecnav2"]').getByTestId('verb-text');
		await expect(again).toHaveValue('Half of what I meant to say');
		await expect(again).toBeFocused();
		// cancel is what forgets it
		await page.locator('[data-testid="comment-expanded"] article.box[data-annotation-id="a-2026-09-16-ecnav2"]').getByTestId('verb-cancel').click();
		await page.locator('[data-testid="comment-expanded"] article.box[data-annotation-id="a-2026-09-16-ecnav2"]').getByTestId('verb-reply').click();
		await expect(page.locator('[data-testid="comment-expanded"]').getByTestId('verb-text')).toHaveValue('');
	});

	test("it is titled by its type's name in its colour with the × on that line, then the body; no status word, author and date on one line", async ({ page }) => {
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		// the title line comes first: the type's name, in the annotation's colour, and the × at its right
		expect(await box.evaluate((el) => el.firstElementChild?.className)).toContain('title');
		const kind = box.getByTestId('box-type');
		await expect(kind).toHaveText('Revision');
		expect(channels(await css(kind, 'color'))).toMatchObject(RED);
		const close = box.locator(':scope > .title .comment-close');
		await expect(close).toHaveCount(1);
		const [k, x] = [await kind.boundingBox(), await close.boundingBox()];
		expect(Math.abs(k!.y + k!.height / 2 - (x!.y + x!.height / 2))).toBeLessThan(6);
		expect(x!.x).toBeGreaterThan(k!.x + k!.width);
		// then the body
		expect(await box.evaluate((el) => el.children[1]?.className)).toContain('body');
		await expect(box.locator('.body').first()).toContainText('parity count');
		const who = box.locator(':scope > .meta .who');
		await expect(who).toHaveText(/^agent · \S/);
		await expect(who).not.toContainText(/revision|open/i);
		expect(channels(await css(box, 'border-left-color'))).toMatchObject(RED);
		await expect(box).toHaveCSS('border-left-width', '3px');
		// no wash of its own: the colour is the stripe and nothing else
		expect(channels(await css(box, 'background-color'))).not.toMatchObject(RED);
	});

	test("the stripe is the annotation's own colour; one whose type the quilt no longer has keeps it, untitled", async ({ page }) => {
		await serve(page, (m) => (m.annotations['a-2026-09-16-bns3an'].type = 'remark'));
		const question = await openBox(page, '/node/sy-0002', 'a-2026-09-16-bns3an');
		expect(channels(await css(question, 'border-left-color'))).toMatchObject(BLUE);
		await expect(question.getByTestId('box-type')).toHaveText('');
		await page.keyboard.press('Escape');
		const suggestion = await openBox(page, '/node/sy-0002', 'a-2026-09-16-hqnbz4');
		expect(channels(await css(suggestion, 'border-left-color'))).toMatchObject(ORANGE);
		await expect(suggestion.getByTestId('box-type')).toHaveText('Suggestion');
	});

	test('no quote on an anchored annotation, whose mark is the quote; the quote, italic, on one with no mark of its own', async ({ page }) => {
		const anchored = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		await expect(anchored.locator('.quote')).toHaveCount(0);
		// a-2026-09-16-a91hwf lost its anchor, so its box is the only record of the words it was about
		const detached = await openBox(page, '/node/sy-0001', 'a-2026-09-16-a91hwf');
		const quote = detached.locator('.quote');
		await expect(quote).toContainText('an involution');
		await expect(quote).toHaveCSS('font-style', 'italic');
	});

	test("a proposal stands at a rule in the annotation's colour, headed by its placement word, rendered, with the verbatim one link away", async ({ page }) => {
		// the fixture's suggestion is resolved, so it is reopened to be drawn
		await serve(page, (m) => (m.annotations['a-2026-09-16-hwtkaw'].status = 'open'));
		const box = await openBox(page, '/node/sy-0004', 'a-2026-09-16-hwtkaw');
		const pay = box.getByTestId('payload');
		await expect(pay).toHaveAttribute('data-placement', 'replace');
		await expect(pay.locator('.word')).toHaveText('replace');
		expect(channels(await css(pay.locator('.word'), 'color'))).toMatchObject(ORANGE);
		expect(channels(await css(pay, 'border-left-color'))).toMatchObject(ORANGE);
		await expect(pay).toHaveCSS('border-left-width', '2px');
		await expect(pay).not.toContainText('proposed in place of');
		// rendered is what opens: the math typeset, the LaTeX that produced it off screen
		await expect(pay.getByTestId('payload-rendered').locator('mjx-container')).not.toHaveCount(0);
		await expect(pay.getByTestId('payload-rendered')).not.toContainText('\\ref');
		await expect(pay.getByTestId('payload-verbatim')).toHaveCount(0);
		const view = pay.getByTestId('payload-view');
		await expect(view).toHaveText('· verbatim');
		await view.click();
		await expect(pay.getByTestId('payload-verbatim')).toContainText('\\ref{sy-0002}');
		await expect(view).toHaveText('· rendered');
	});

	test('a proposed theorem and proof read as the document prints them, from the publisher, never as a typesetting error', async ({ page }) => {
		const tex = '\\begin{theorem}\\label{sy-0004-ai}\nEvery orbit has \\(1\\) or \\(2\\) points.\n\\end{theorem}\n\\begin{proof}\nBy definition.\n\\end{proof}';
		await serve(page, (m) => {
			m.annotations['a-2026-09-16-hwtkaw'].status = 'open';
			m.annotations['a-2026-09-16-hwtkaw'].payload = tex;
			m.annotations['a-2026-09-16-hwtkaw'].payload_html =
				'<div class="env env-theorem" data-taxon="Theorem" data-style="plain"><p class="env-label"><span class="taxon">Theorem</span></p><p>Every orbit has <span class="math inline">\\(1\\)</span> or <span class="math inline">\\(2\\)</span> points.</p></div><details class="env env-proof" open><summary class="env-label">Proof</summary><p>By definition.</p></details>';
		});
		const box = await openBox(page, '/node/sy-0004', 'a-2026-09-16-hwtkaw');
		const rendered = box.getByTestId('payload-rendered');
		await expect(rendered.locator('.env-theorem .taxon')).toHaveText('Theorem');
		await expect(rendered.locator('.env-proof')).toContainText('By definition.');
		await expect(rendered.locator('mjx-container').first()).toBeAttached();
		await expect(rendered.locator('mjx-merror')).toHaveCount(0);
		await expect(rendered).not.toContainText('\\begin');
		// the verbatim view is still the TeX as written
		await box.getByTestId('payload-view').click();
		await expect(box.getByTestId('payload-verbatim')).toHaveText(tex);
	});

	test('a verbatim proposal is one block: its lines kept, never a strip per line overlapping the one above, the switch beside the placement word', async ({ page }) => {
		const long = ['if and only if \\(x\\) is in the image of \\(\\eta(U)\\colon\\mathcal Y^G(U)\\to \\mathcal Y(U)\\): indeed \\(\\mathcal Y^G\\) parameterizes group-theoretic sections', '  of \\(\\mathcal Y\\) \\cite[Lemma 4.1.2]{Kre99}.'].join('\n');
		await serve(page, (m) => {
			m.annotations['a-2026-09-16-hwtkaw'].status = 'open';
			m.annotations['a-2026-09-16-hwtkaw'].payload = long;
		});
		const box = await openBox(page, '/node/sy-0004', 'a-2026-09-16-hwtkaw');
		const pay = box.getByTestId('payload');
		await pay.getByTestId('payload-view').click();
		const pre = pay.getByTestId('payload-verbatim');
		await expect(pre).toBeVisible();
		const drawn = await pre.evaluate((el) => {
			const cs = getComputedStyle(el);
			return { display: cs.display, boxes: el.getClientRects().length, line: parseFloat(cs.lineHeight), size: parseFloat(cs.fontSize), text: el.textContent };
		});
		expect(drawn.display).toBe('block');
		expect(drawn.boxes).toBe(1);
		expect(drawn.line).toBeGreaterThan(drawn.size * 1.3);
		expect(drawn.text).toBe(long);
		// the switch stays on the placement word's line, above the text, whichever way it is shown
		const word = await pay.locator('.word').boundingBox();
		const view = await pay.getByTestId('payload-view').boundingBox();
		expect(Math.abs(view!.y - word!.y)).toBeLessThan(6);
	});

	test('a suggestion shows its key with it in place, its new words marked, and the patch that takes it', async ({ page }) => {
		// the publisher renders both at build: the key with the payload in place of exactly the quoted words, and the patch `loom suggestion` prints
		const id = 'a-2026-09-16-hwtkaw';
		await serve(page, (m) => {
			m.annotations[id].status = 'open';
			m.annotations[id].change = { state: 'ready', fragment: 'fragments/suggestions/s.html', diff: 'fragments/suggestions/s.diff', moved: true };
		});
		await page.route('**/fragments/suggestions/s.html', (r) =>
			r.fulfill({ contentType: 'text/html', body: '<div class="env env-proof"><p>By Lemma 1.2, <mark class="review-changed">\\(X\\) is the</mark> disjoint union of orbits of size one or two.</p></div>' })
		);
		await page.route('**/fragments/suggestions/s.diff', (r) =>
			r.fulfill({
				contentType: 'text/plain',
				body: '--- a/nodes/sy-0003.tex\n+++ b/nodes/sy-0003.tex\n@@ -10 +10 @@\n-By Lemma~\\ref{sy-0002} the set $X$ is a disjoint union of orbits of size one or two.\n+By Lemma~\\ref{sy-0002}, $X$ is the disjoint union of orbits of size one or two.\n'
			})
		);
		const box = await openBox(page, '/node/sy-0004', id);
		await box.getByTestId('payload-in-place').click();
		await expect(box.getByTestId('payload-in-place').getAttribute('aria-pressed')).resolves.toBe('true');
		await expect(box.getByTestId('payload-in-place-view').locator('mark.review-changed')).toBeVisible();
		// the key changed since the suggestion was written, though the words it quotes still stand
		await expect(box.getByTestId('payload-moved')).toBeVisible();
		await box.getByTestId('payload-patch').click();
		await expect(box.getByTestId('payload-patch-view')).toContainText('the set $X$ is a disjoint union');
		await expect(box.getByTestId('payload-patch-view')).toContainText('$X$ is the disjoint union');
		// the view shown, chosen again, gives the payload back
		await box.getByTestId('payload-patch').click();
		await expect(box.getByTestId('payload-rendered')).toBeVisible();
	});

	test('a suggestion with no place in the text says why, and one already taken offers resolve as applied', async ({ page }) => {
		const id = 'a-2026-09-16-hwtkaw';
		await serve(page, (m) => {
			m.annotations[id].status = 'open';
			m.annotations[id].change = { state: 'unplaced', why: 'the text a-2026-09-16-hwtkaw quotes no longer stands in sy-0004' };
		});
		let box = await openBox(page, '/node/sy-0004', id);
		await expect(box.getByTestId('payload-unplaced')).toContainText('no longer stands');
		await expect(box.getByTestId('payload-in-place')).toHaveCount(0);
		await expect(box.getByTestId('payload-rendered')).toBeVisible();

		await page.unroute('**/build/manifest.json');
		await writes(page, ['resolve']);
		let sent: Record<string, unknown> | null = null;
		await page.route('**/_api/resolve', async (r) => {
			sent = JSON.parse(r.request().postData() ?? '{}');
			await r.fulfill({ json: { ok: true, result: `resolved as applied ${id}` } });
		});
		await serve(page, (m) => {
			m.annotations[id].status = 'open';
			m.annotations[id].change = { state: 'taken' };
		});
		await page.goto('/node/sy-0004');
		await pickSession(page, REFEREE);
		box = await openBox(page, '/node/sy-0004', id);
		await expect(box.getByTestId('payload-taken')).toHaveText('The text now reads as this suggestion taken.');
		await box.getByTestId('verb-applied').click();
		await expect.poll(() => sent).toMatchObject({ annotation: id, applied: true });
	});

	test('a suggestion resolved as applied says so once', async ({ page }) => {
		const id = 'a-2026-09-16-hwtkaw';
		await serve(page, (m) => (m.annotations[id].applied = { hash: 'abc' }));
		// settled, so drawn only while settled annotations are shown
		await page.goto('/node/sy-0004');
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		await page.locator(`.fragment .annotation[data-annotation~="${id}"]`).first().click();
		const box = page.locator(`[data-testid="comment-expanded"] article.box[data-annotation-id="${id}"]`);
		await expect(box.getByTestId('outcome')).toHaveText(' · taken');
	});

	test('resolve is offered only where the type stays open until resolved; one that only informs, or none, has reply, edit and delete', async ({ page }) => {
		await serve(page, (m) => {
			m.annotations['a-2026-09-16-bns3an'].type = 'note';
			m.annotations['a-2026-09-16-hqnbz4'].type = null;
		});
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'delete']);
		const asks = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		await expect(asks.getByTestId('verb-resolve')).toBeVisible();
		for (const id of ['a-2026-09-16-bns3an', 'a-2026-09-16-hqnbz4']) {
			const box = await openBox(page, '/node/sy-0002', id);
			await expect(box.getByTestId('verb-reply')).toBeVisible();
			await expect(box.getByTestId('verb-edit')).toBeVisible();
			await expect(box.getByTestId('verb-delete')).toBeVisible();
			await expect(box.getByTestId('verb-resolve')).toHaveCount(0);
		}
	});

	test('reply and edit open inside the box beneath the meta line, and nothing pops over the text', async ({ page }) => {
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'delete']);
		await prefs(page, { comments: 'inline' });
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		const meta = box.locator(':scope > .meta');
		const row = meta.getByTestId('verb-row');
		await expect(row).toBeVisible();
		await expect(row.getByTestId('verb-reply')).toHaveCSS('color', 'rgb(136, 135, 128)'); // --ink-faint: quiet until reached for

		await row.getByTestId('verb-reply').click();
		const panel = box.getByTestId('verb-panel');
		await expect(panel).toBeVisible();
		await expect(page.locator('.pop')).toHaveCount(0);
		await expect(panel).toHaveCSS('position', 'static');
		// beneath the verbs, inside the box: the box grows to hold it
		const [pb, rb, bb] = await Promise.all([panel.boundingBox(), row.boundingBox(), box.boundingBox()]);
		expect(pb!.y).toBeGreaterThanOrEqual(rb!.y + rb!.height - 1);
		expect(pb!.y + pb!.height).toBeLessThanOrEqual(bb!.y + bb!.height + 1);
		await expect(panel.getByTestId('verb-text')).toHaveAttribute('placeholder', 'reply');
		// it says nothing until it has something to say
		await expect(panel.getByTestId('verb-send')).toBeDisabled();
		await panel.getByTestId('verb-text').fill('Fixed in the next revision.');
		await expect(panel.getByTestId('verb-send')).toBeEnabled();
		await page.keyboard.press('Escape');
		await expect(panel).toHaveCount(0);

		// an edit starts from the body it supersedes, with the quilt's types to hand and its own chosen
		await row.getByTestId('verb-edit').click();
		await expect(panel.getByTestId('verb-text')).toHaveValue(/parity count/);
		await expect(panel.getByTestId('verb-type')).toHaveValue('revision');
		await expect(panel.getByTestId('verb-type').locator('option')).toHaveText(['No type', 'Revision', 'Suggestion', 'Question', 'Note']);
		await expect(page.getByTestId('verb-more')).toHaveCount(0);
	});

	test('delete asks nothing first: the box goes with the annotation, and Undo at the foot of the window puts back what loom took out', async ({ page }) => {
		const removed = [{ event: 'created', id: 'a-2026-09-16-ecnav2' }, { event: 'replied', id: 'a-2026-09-16-hwnav1' }];
		const sent: Record<string, Record<string, unknown>> = {};
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'delete', 'restore']);
		await page.addInitScript((id) => localStorage.setItem('arras.session-view', JSON.stringify({ selected: id, view: 'all', showClosed: false })), REFEREE);
		await page.route('**/_api/delete', (r) => ((sent.delete = r.request().postDataJSON()), r.fulfill({ json: { ok: true, result: 'deleted a-2026-09-16-ecnav2', removed } })));
		await page.route('**/_api/restore', (r) => ((sent.restore = r.request().postDataJSON()), r.fulfill({ json: { ok: true, result: 'restored a-2026-09-16-ecnav2' } })));
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		await box.locator(':scope > .meta').getByTestId('verb-delete').click();
		await expect(box.getByTestId('verb-panel')).toHaveCount(0);
		expect(sent.delete).toMatchObject({ annotation: 'a-2026-09-16-ecnav2', session: REFEREE });
		const held = page.getByTestId('deleted');
		await expect(held).toHaveCount(1);
		await expect(held).toContainText('Deleted Revision on Theorem 2.1.');
		await held.getByTestId('deleted-undo').click();
		await expect(held).toHaveCount(0);
		expect(sent.restore).toMatchObject({ events: removed, session: REFEREE });
	});

	test('a refused delete says why in the box, and holds nothing to undo', async ({ page }) => {
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'delete']);
		await page.addInitScript((id) => localStorage.setItem('arras.session-view', JSON.stringify({ selected: id, view: 'all', showClosed: false })), REFEREE);
		await page.route('**/_api/delete', (r) => r.fulfill({ status: 400, json: { ok: false, error: { code: 'refused', message: 'an agent deletes only its own annotations' } } }));
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-ecnav2');
		await box.locator(':scope > .meta').getByTestId('verb-delete').click();
		await expect(box.getByTestId('verb-said')).toHaveText('an agent deletes only its own annotations');
		await expect(page.getByTestId('deleted')).toHaveCount(0);
	});

	test('a settled box: the stripe at half strength, the body softened, the outcome said once, and reopen and delete its verbs', async ({ page }) => {
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'delete']);
		await page.goto('/node/sy-0004');
		// a-2026-09-16-hwtkaw is resolved: its mark is drawn only once settled annotations are shown
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-hwtkaw"]');
		await expect(mark).toHaveClass(/settled/);
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		await mark.click();
		const box = page.locator('[data-testid="comment-expanded"] article.box[data-annotation-id="a-2026-09-16-hwtkaw"]');
		await expect(box).toHaveClass(/settled/);
		const stripe = channels(await css(box, 'border-left-color'));
		expect(stripe).toMatchObject(ORANGE);
		expect(stripe.a).toBeCloseTo(0.5, 1);
		await expect(box.locator('.body').first()).toHaveCSS('color', 'rgb(95, 94, 90)'); // --ink-soft
		// a suggestion with text, resolved without being taken
		await expect(box.locator(':scope > .meta .who')).toContainText('· left');
		await expect(box.locator(':scope > .meta .who')).not.toContainText('resolved');
		const row = box.locator(':scope > .meta').getByTestId('verb-row');
		await expect(row.getByTestId('verb-reopen')).toBeVisible();
		await expect(row.locator('button')).toHaveText(['reopen', 'delete']);
	});

	test('travel is two-way: a double-click on a mark lands on its box, and one on the box lands on its mark', async ({ page }) => {
		await page.goto('/master/drafting/main');
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]');
		await mark.dblclick();
		const box = page.locator('article.box[data-annotation-id="a-2026-09-16-ecnav2"]');
		await expect(box).toHaveCount(1);
		await expect(box).toHaveClass(/travelled/);
		await expect(page.getByTestId('travel-nowhere')).toHaveCount(0);
		await box.locator('.body').first().dblclick();
		await expect(mark).toHaveClass(/travelled/);
		await expect(box).toHaveCount(1);
	});

	test('beside a comparison a card in the flow is the annotation\'s one box: its mark travels to it rather than opening a second', async ({ page }) => {
		await page.goto('/master/drafting/main?review=sy-0001&cause=0');
		const card = page.locator('aside.comment-slot.inline article.box[data-annotation-id="a-2026-09-16-ecnav2"]');
		await expect(card).toHaveCount(1);
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]').click();
		await expect(card).toHaveClass(/travelled/);
		await expect(page.locator('article.box[data-annotation-id="a-2026-09-16-ecnav2"]')).toHaveCount(1);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
	});
});

test.describe('the placement', () => {
	test('the placement is a display setting', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await settings(page, 'appearance');
		await page.getByTestId('comments-inline').click();
		await expect(page.locator('html')).toHaveAttribute('data-comments', 'inline');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);
	});

	test('changing the placement re-wires the document without typesetting it again', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		await page.goto('/master/drafting/main');
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mjx-container');
		await page.waitForFunction(() => document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0);
		await page.evaluate(() => {
			const w = window as unknown as { MathJax: { typesetPromise: (els: Element[]) => Promise<void> }; typeset: string[] };
			const real = w.MathJax.typesetPromise.bind(w.MathJax);
			w.typeset = [];
			// a comment card typesets its own body; what must not happen is the document's text going through MathJax again
			w.MathJax.typesetPromise = (els) => {
				w.typeset.push(els.some((e) => e.closest('.fragment') && !e.closest('aside.comment-slot')) ? 'document' : 'card');
				return real(els);
			};
		});
		await settings(page, 'appearance');
		await page.getByTestId('comments-inline').click();
		await page.waitForSelector('.fragment[data-comments-wired="inline"]');
		await page.getByTestId('comments-floating').click();
		await page.waitForSelector('.fragment[data-comments-wired="floating"]');
		// a later event rendered: a mark opened after the switch draws its box, so any re-typeset the switch set off has had its turn
		await page.keyboard.press('Escape');
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-ecnav2"]').click();
		await expect(page.locator('aside.comment-slot.floating article.box').first()).toBeVisible();
		expect(await page.evaluate(() => (window as unknown as { typeset: string[] }).typeset)).not.toContain('document');
	});
});

test.describe('writing', () => {
	/** Advertise `caps` from the publisher's write API and accept every write; `vite preview` serves none, and the controls appear only where one is. */
	async function writes(page: Page, caps: string[]): Promise<void> {
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: caps, token: 't' } }));
		await page.route('**/_api/*', (r) => r.fulfill({ json: { ok: true, result: 'done' } }));
	}

	test('with no write API there is no editing affordance at all: no verbs on what is written, no tools to write with', async ({ page }) => {
		// detected, never assumed: the fixture is served by a static preview with no write API, which is also what a deployed static site gets
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		await expect(pane(page, 1).getByTestId('context')).toBeVisible();
		await pane(page, 0).locator('.fragment mark.annotation').first().click();
		await expect(page.locator('article.box').first()).toBeVisible();
		await expect(page.getByTestId('verb-row')).toHaveCount(0);
		await expect(page.getByTestId('tool-select')).toHaveCount(0);
	});

	test('a verb that needs no panel still shows why it was refused', async ({ page }) => {
		// `resolve` is one click and opens no panel, so its refusal is shown in the box: the viewer's own when nothing is selected, the publisher's once the write reaches it
		await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['annotate', 'reply', 'resolve', 'edit', 'delete'], token: 't' } }));
		await page.route('**/_api/resolve', (route) =>
			route.fulfill({
				status: 400,
				contentType: 'application/json',
				body: JSON.stringify({ error: { code: 'refused', message: 'no author name: add name = "Your Name" under [author]' } })
			})
		);
		await page.goto('/node/sy-0003');
		const openFirstMark = async () => {
			await page.locator('[data-pane] .fragment mark.annotation').first().click();
			await expect(page.locator('[data-testid="comment-expanded"] article.box').first()).toBeVisible();
		};
		await openFirstMark();
		const said = page.getByTestId('verb-said').first();
		// with nothing selected the write never leaves the viewer, and the verb says which condition is unmet
		await page.getByTestId('verb-resolve').first().click();
		await expect(said).toContainText('No session selected');
		// with one selected the request reaches the publisher, and its refusal is what gets shown
		await pickSession(page, REFEREE);
		await openFirstMark();
		await page.getByTestId('verb-resolve').first().click();
		await expect(said).toBeVisible();
		await expect(said).toContainText('no author name');
	});

	test("words selected in an annotation's box are not the document's, and offer nothing to annotate", async ({ page }) => {
		// a box stands in the fragment's markup, but a note quoting its words would be filed on the node with a quote its source does not hold
		await writes(page, ['annotate', 'reply']);
		await page.goto('/node/sy-0003');
		await page.locator('.fragment .annotation[data-annotation~="a-2026-09-16-ecnav2"]').first().click();
		const body = page.locator('[data-testid="comment-expanded"] article.box[data-annotation-id="a-2026-09-16-ecnav2"] .body').first();
		await expect(body).toBeVisible();
		await selectWithin(body);
		await page.waitForTimeout(300);
		await expect(page.getByTestId('annotate-offer')).toHaveCount(0);
		// the document's own words still offer it
		await selectWithin(pane(page, 0).locator('.fragment .env[data-id="sy-0003"] p[data-src]').first());
		await expect(page.getByTestId('annotate-offer')).toHaveCount(1);
	});

	test('a selection offers one annotate chip at its end, in the annotation neutral at the reader\'s body size, opaque under the pointer, and Enter does what the chip does', async ({ page }) => {
		await writes(page, ['annotate']);
		await page.goto('/node/sy-0002');
		const words = pane(page, 0).locator('.fragment .env[data-id="sy-0002"] p[data-src]').first();
		await expect(words).toBeVisible();
		await selectWithin(words);
		const chip = page.getByTestId('annotate-offer');
		await expect(chip).toHaveText('annotate');
		await expect(chip).toHaveCSS('color', 'rgb(111, 109, 102)');
		// after the selection's last line, not above its first
		const end = await words.evaluate((el) => {
			const r = [...(window.getSelection()!.getRangeAt(0).getClientRects())].at(-1)!;
			return { right: r.right, top: r.top, bottom: r.bottom };
		});
		const at = (await chip.boundingBox())!;
		expect(at.x).toBeGreaterThanOrEqual(end.right);
		expect(at.y + at.height / 2).toBeGreaterThan(end.top - 1);
		expect(at.y + at.height / 2).toBeLessThan(end.bottom + 1);
		// set at the reader's body size, and its hover face opaque, so the words under it never show through its label
		const body = await page.locator('.arras').first().evaluate((el) => getComputedStyle(el).getPropertyValue('--body-size').trim());
		await expect(chip).toHaveCSS('font-size', body);
		await chip.hover();
		expect(channels(await css(chip, 'background-color')).a).toBe(1);
		// Enter opens the composer, and the chip is gone once it is open
		await page.keyboard.press('Enter');
		await expect(page.getByTestId('note-at')).toBeVisible();
		await expect(chip).toHaveCount(0);
	});

	test('with the box tool chosen, a drag that starts on a mark draws a box, and a click on it still opens the mark', async ({ page }) => {
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate'], token: 't' } }));
		await page.goto('/node/sy-0003');
		const mark = pane(page, 0).locator('.fragment mark.annotation').first();
		await expect(mark).toBeVisible();
		await page.getByTestId('tool-box').click();
		// a click without a drag is still a click on the mark
		await mark.click();
		await expect(pane(page, 0).getByTestId('comment-expanded')).toBeVisible();
		await page.keyboard.press('Escape');
		// a drag from it is a box
		const b = (await mark.boundingBox())!;
		await page.mouse.move(b.x + 4, b.y + b.height / 2);
		await page.mouse.down();
		await page.mouse.move(b.x + 120, b.y + b.height + 30, { steps: 8 });
		await page.mouse.up();
		await expect(page.getByTestId('note-at')).toBeVisible();
	});
});

// The composer (annotation study fixes 5 and 18–21): the header names the words, the quilt's types are buttons, and × or Escape cancel. Against a mocked write API: what is tested here is the form, not the write, which the write suite holds against the real publisher.
test.describe('the composer', () => {
	async function writes(page: Page): Promise<void> {
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['annotate'], token: 't' } }));
	}

	/** Open the composer on the statement of `key`, by selecting its first paragraph and taking the chip. */
	async function composeOn(page: Page, key: string) {
		await writes(page);
		await page.goto(`/node/${key}`);
		const words = pane(page, 0).locator(`.fragment .env[data-id="${key}"] > p[data-src]`).first();
		await expect(words).toBeVisible();
		await selectWithin(words);
		await page.getByTestId('annotate-offer').click();
		const form = page.getByTestId('note-at');
		await expect(form).toBeVisible();
		return form;
	}

	test('the header names the quoted words and the place as the tab names it, never the key', async ({ page }) => {
		const form = await composeOn(page, 'sy-0003');
		const where = form.getByTestId('note-where');
		await expect(where).toContainText('finite widget');
		await expect(where).toContainText('in Theorem 2.1');
		await expect(where).not.toContainText('sy-0003');
		// the words are set in the body face, as a quotation
		await expect(where.locator('q.quoted')).toHaveCSS('font-style', 'italic');
	});

	test('a box round a labelled equation names the whole of the equation', async ({ page }) => {
		await writes(page);
		await page.goto('/node/sy-0001');
		const display = pane(page, 0).locator('.fragment .math.display[data-label="eq:fix"]');
		await expect(display.locator('mjx-container')).toBeVisible();
		await page.getByTestId('tool-box').click();
		const b = (await display.boundingBox())!;
		await page.mouse.move(b.x + 4, b.y + 2);
		await page.mouse.down();
		await page.mouse.move(b.x + b.width - 4, b.y + b.height - 2, { steps: 6 });
		await page.mouse.up();
		const form = page.getByTestId('note-at');
		await expect(form).toBeVisible();
		await expect(form.getByTestId('note-where')).toHaveText('on the whole of equation (2) in Definition 1.1');
		await expect(form.getByTestId('note-where')).not.toContainText('sy-0001');
		// a box defaults to no type, as a selection does
		await expect(form.getByTestId('note-type').locator('[aria-pressed="true"]')).toHaveAttribute('data-type', '');
	});

	test("the quilt's types as buttons in their colours, then No type, chosen by default; words are needed only for a type that stays open; the type is sent by its id, and none for No type", async ({ page }) => {
		const sent: Record<string, unknown>[] = [];
		await page.route('**/_api/annotate', (r) => (sent.push(r.request().postDataJSON()), r.fulfill({ json: { ok: true, result: 'a-2026-11-11-zz0001' } })));
		const form = await composeOn(page, 'sy-0003');
		await pickSession(page, REFEREE);
		const types = form.getByTestId('note-type');
		const submit = form.getByTestId('note-submit');
		await expect(types.locator('button')).toHaveText(['Revision', 'Suggestion', 'Question', 'Note', 'No type']);
		await expect(types.locator('[aria-pressed="true"]')).toHaveAttribute('data-type', '');
		await expect(types.locator('[data-type="revision"]')).toHaveCSS('color', 'rgb(204, 28, 28)');
		await expect(types.locator('[data-type="suggestion"]')).toHaveCSS('color', 'rgb(196, 90, 10)');
		await expect(types.locator('[data-type="question"]')).toHaveCSS('color', 'rgb(26, 111, 196)');
		await expect(types.locator('[data-type="note"]')).toHaveCSS('color', 'rgb(136, 135, 128)');
		await expect(types.locator('[data-type=""]')).toHaveCSS('color', 'rgb(111, 109, 102)');
		await expect(submit).toHaveText('Annotate');
		// with no type, nothing need be said
		await expect(submit).toBeEnabled();
		const height = (await form.boundingBox())!.height;
		// a type that stays open until resolved needs words, and the submit takes its colour
		await types.locator('[data-type="revision"]').click();
		await expect(types.locator('[aria-pressed="true"]')).toHaveAttribute('data-type', 'revision');
		await expect(submit).toBeDisabled();
		await expect(submit).toHaveCSS('background-color', 'rgb(204, 28, 28)');
		// one that only informs does not
		await types.locator('[data-type="note"]').click();
		await expect(submit).toBeEnabled();
		expect((await form.boundingBox())!.height).toBe(height);
		await types.locator('[data-type="revision"]').click();
		await form.getByTestId('note-body').fill('Say which orbit.');
		await submit.click();
		await expect(form).toHaveCount(0);
		expect(sent).toHaveLength(1);
		expect(sent[0]).toMatchObject({ target: 'sy-0003', type: 'revision', message: 'Say which orbit.' });
		expect(sent[0]).not.toHaveProperty('kind');
		expect(sent[0]).not.toHaveProperty('severity');
		// No type sends none, and no words when none were written
		const again = await composeOn(page, 'sy-0003');
		await again.getByTestId('note-submit').click();
		await expect(again).toHaveCount(0);
		expect(sent).toHaveLength(2);
		expect(sent[1]).not.toHaveProperty('type');
		expect(sent[1]).not.toHaveProperty('message');
	});

	test('× and Escape cancel, and there is no third button', async ({ page }) => {
		const form = await composeOn(page, 'sy-0003');
		await expect(form.locator('button', { hasText: /^cancel$/i })).toHaveCount(0);
		await page.keyboard.press('Escape');
		await expect(form).toHaveCount(0);
		await composeOn(page, 'sy-0003');
		await form.getByTestId('note-close').click();
		await expect(form).toHaveCount(0);
	});
});

// The settled control: a resolved annotation is not drawn at rest; `show settled annotations` under the toolbar's *view*, or `s`, draws it faintly for the sitting and on every page, and a fresh visit starts with it off.
test.describe('the settled control', () => {
	const settledMark = (page: Page) => page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-hwtkaw"]');

	/** The control, read where it stands: under *view*, which is opened to read it. */
	async function settled(page: Page) {
		await viewMenu(page);
		return page.getByTestId('toggle-settled');
	}

	/** Close the menu with Escape, which leaves the page as it was. */
	const shut = (page: Page) => page.keyboard.press('Escape');

	test('on a document it shows and hides the settled marks, and their boxes open only while it is on', async ({ page }) => {
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
		// show all now opens the settled boxes too
		await viewMenu(page);
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('article.box[data-annotation-id="a-2026-09-16-hwtkaw"]')).toBeVisible();
		await (await settled(page)).click();
		await expect(await settled(page)).toHaveText(/^show settled annotations/);
		await shut(page);
		expect((await drawn(m)).band.a).toBe(0);
		await expect(page.locator('article.box[data-annotation-id="a-2026-09-16-hwtkaw"]')).toHaveCount(0);
		await expect(page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-tc3rcf"]')).toHaveCount(0);
	});

	test('on a node the same control, and the s key beside e and h', async ({ page }) => {
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

	test('it is off again on a fresh visit', async ({ page }) => {
		await page.goto('/master/drafting/main');
		await (await settled(page)).click();
		await expect(await settled(page)).toHaveText(/^hide settled annotations/);
		await page.goto('/master/drafting/main');
		await expect(await settled(page)).toHaveText(/^show settled annotations/);
		expect((await drawn(settledMark(page))).band.a).toBe(0);
	});

	test('a link to a settled annotation turns it on and opens the box, one with no quote included', async ({ page }) => {
		// a row in What it did or the Context links a settled annotation by `quilt:`; following it is a request to see it, so the control comes on for the sitting and the box opens, rather than the reader landing on a page where nothing is drawn
		await page.goto(`/session/${REFEREE}?view=did`);
		await page.locator('[data-testid="did-annotation"][href="quilt:a-2026-09-16-hwtkaw"]').click();
		await expect(page.getByTestId('toolbar-view-on')).toBeVisible();
		await expect(page.locator('[data-pane="1"] article.box.settled[data-annotation-id="a-2026-09-16-hwtkaw"]')).toBeVisible();
		// a resolved annotation with no quote is a label mark only while settled annotations are drawn, and its box opens from it and says it was resolved
		await page.goto('/node/sy-0003');
		const label = page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-tc3rcf"]');
		await expect(label).toHaveCount(0);
		await viewMenu(page);
		await page.getByTestId('toggle-settled').click();
		await label.click();
		const box = page.locator('article.box[data-annotation-id="a-2026-09-16-tc3rcf"]');
		await expect(box).toBeVisible();
		await expect(box.getByTestId('outcome')).toHaveText('· resolved');
	});
});
