// Annotations as a reader meets them: marks in the text, the boxes they open floating or inline, all of them opened at once, what a suggestion proposes, and the verbs and tools that write one where a publisher serves. Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { beside, pane, prefs } from '../workspace';
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

/** The hue and weight a mark is drawn with, and what is under its words. */
async function drawn(mark: import('@playwright/test').Locator): Promise<{ hue: ReturnType<typeof channels>; weight: string; wash: ReturnType<typeof channels>; outline: string }> {
	return {
		hue: channels(await css(mark, 'border-bottom-color')),
		weight: await css(mark, 'border-bottom-width'),
		wash: channels(await css(mark, 'background-color')),
		outline: await css(mark, 'outline-style')
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

const OBJECTION = { r: 163, g: 45, b: 45 };
const SUGGESTION = { r: 160, g: 122, b: 10 };
const QUESTION = { r: 24, g: 95, b: 165 };
const CITATION = { r: 107, g: 63, b: 160 };
const NEUTRAL = { r: 111, g: 109, b: 102 };

// The mark is `style()` of the record (book 15.3.1): hue is the kind, weight is the severity, the wash is the hue at 5% and at 10% on the mark whose box is open, and a settled annotation is not drawn. Each test holds one clause of that rule against the computed style, never a pixel.
test.describe('marks', () => {
	const mark = (page: Page, id: string) => page.locator(`.fragment mark.annotation[data-annotation~="${id}"]`);

	test('an objection is underlined in red', async ({ page }) => {
		await page.goto('/master/main');
		const m = mark(page, 'a-2026-09-16-0001');
		await expect(m).toHaveClass(/k-objection/);
		expect((await drawn(m)).hue).toMatchObject({ ...OBJECTION, a: 1 });
	});

	test('a suggestion is underlined in yellow', async ({ page }) => {
		// the one open suggestion is read in the talk, where its mark is baked
		await page.goto('/master/talk');
		const m = mark(page, 'a-2026-09-16-0007');
		await expect(m).toHaveClass(/k-suggestion/);
		expect((await drawn(m)).hue).toMatchObject({ ...SUGGESTION, a: 1 });
	});

	test('a question is underlined in blue', async ({ page }) => {
		await page.goto('/master/main');
		const m = mark(page, 'a-2026-09-16-0006');
		await expect(m).toHaveClass(/k-question/);
		expect((await drawn(m)).hue).toMatchObject({ ...QUESTION, a: 1 });
	});

	test('a citation is underlined in violet', async ({ page }) => {
		// the fixture's citations have no quote, so the mark is on the label
		await page.goto('/master/main');
		const m = page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-0005"]');
		await expect(m).toHaveClass(/k-citation/);
		expect((await drawn(m)).hue).toMatchObject({ ...CITATION, a: 1 });
	});

	test('a note, and any kind the viewer has never heard of, is underlined in the neutral', async ({ page }) => {
		await serve(page, (m) => {
			m.annotations['a-2026-09-16-0006'].kind = 'note';
			m.annotations['a-2026-09-16-0001'].kind = 'catastrophe';
		});
		await page.goto('/master/main');
		const note = mark(page, 'a-2026-09-16-0006');
		await expect(note).toHaveClass(/k-note/);
		expect((await drawn(note)).hue).toMatchObject({ ...NEUTRAL, a: 1 });
		expect((await drawn(mark(page, 'a-2026-09-16-0001'))).hue).toMatchObject({ ...NEUTRAL, a: 1 });
	});

	test('weight is severity: 1px minor, 3px major, 2px for moderate and for the kinds that take none', async ({ page }) => {
		// the fixture's minor suggestion is resolved, so it is reopened to be drawn
		await serve(page, (m) => (m.annotations['a-2026-09-16-0002'].status = 'open'));
		await page.goto('/master/main');
		const major = mark(page, 'a-2026-09-16-0001');
		await expect(major).toHaveClass(/s-major/);
		expect((await drawn(major)).weight).toBe('3px');
		const minor = mark(page, 'a-2026-09-16-0002');
		await expect(minor).toHaveClass(/s-minor/);
		expect((await drawn(minor)).weight).toBe('1px');
		const ungraded = mark(page, 'a-2026-09-16-0006');
		await expect(ungraded).not.toHaveClass(/s-/);
		expect((await drawn(ungraded)).weight).toBe('2px');
	});

	test('the words are washed in the hue at 5% at rest and at 10% on the one mark whose box is open, and nothing is outlined', async ({ page }) => {
		await page.goto('/master/main');
		const m = mark(page, 'a-2026-09-16-0001');
		const other = mark(page, 'a-2026-09-16-0006');
		const rest = await drawn(m);
		expect(rest.wash).toMatchObject(OBJECTION);
		expect(rest.wash.a).toBeCloseTo(0.05, 2);
		expect((await drawn(other)).wash).toMatchObject(QUESTION);
		expect((await drawn(other)).wash.a).toBeCloseTo(0.05, 2);
		await m.click();
		await expect(m).toHaveClass(/\bopen\b/);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(1);
		const open = await drawn(m);
		expect(open.wash).toMatchObject(OBJECTION);
		expect(open.wash.a).toBeCloseTo(0.1, 2);
		expect(open.outline).toBe('none');
		// the stronger wash says which box is open, so the other mark stays as it was
		expect((await drawn(other)).wash.a).toBeCloseTo(0.05, 2);
		await page.keyboard.press('Escape');
		await expect(m).not.toHaveClass(/\bopen\b/);
		expect((await drawn(m)).wash.a).toBeCloseTo(0.05, 2);
	});

	test('an annotation with no mark of its own is a mark on its node\'s label, and several share one', async ({ page }) => {
		// a-2026-09-16-0005 has no quote and a-2026-09-16-0010 lost its anchor; both are put on sy-0002's label
		await serve(page, (m) => (m.annotations['a-2026-09-16-0010'].target.key = 'sy-0002'));
		await page.goto('/master/main');
		const label = page.locator('.fragment .env[data-key="sy-0002"] > .env-label mark.annotation-label');
		await expect(label).toHaveCount(1);
		await expect(label).toHaveAttribute('data-annotation', 'a-2026-09-16-0005 a-2026-09-16-0010');
		await expect(label).toContainText('Lemma');
		// no count is drawn anywhere: the label's own words are underlined and nothing is added to them
		await expect(page.locator('.fragment button.comment-count')).toHaveCount(0);
		await label.click();
		const boxes = page.locator('aside.comment-slot.expanded article.box');
		await expect(boxes).toHaveCount(2);
		await expect(page.locator('aside.comment-slot.expanded article.box[data-annotation-id="a-2026-09-16-0005"]')).toHaveCount(1);
		// the label mark takes the hue of its leading annotation, as any mark does
		await expect(label).toHaveClass(/k-citation/);
	});

	test('a phrase with two annotations is one mark whose box lists both, with no count drawn', async ({ page }) => {
		// the reply on the objection's phrase is made an annotation of its own, so the one mark carries two
		await serve(page, (m) => (m.annotations['a-2026-09-16-0008'].in_reply_to = null));
		await page.goto('/node/sy-0003');
		const m = mark(page, 'a-2026-09-16-0001');
		await expect(m).toHaveCount(1);
		await expect(m).toHaveAttribute('data-annotation', 'a-2026-09-16-0001 a-2026-09-16-0008');
		await expect(m).not.toHaveAttribute('data-count');
		expect(await m.evaluate((el) => getComputedStyle(el, '::after').content)).toBe('none');
		await m.click();
		await expect(page.locator('aside.comment-slot.expanded article.box')).toHaveCount(2);
	});

	test('a settled annotation is not drawn until settled annotations are shown, and then faintly, the words untouched', async ({ page }) => {
		// a-2026-09-16-0002 is resolved
		await page.goto('/node/sy-0004');
		const m = mark(page, 'a-2026-09-16-0002');
		await expect(m).toHaveClass(/settled/);
		await expect(m).toContainText('disjoint union of orbits');
		expect((await drawn(m)).hue.a).toBe(0);
		expect((await drawn(m)).wash.a).toBe(0);
		await expect(m).toHaveAttribute('tabindex', '-1');
		// nothing to open: a click on the words is a click on the words, and show all opens nothing
		await m.dispatchEvent('click');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		await page.getByTestId('toggle-annotations').click();
		// shown by the rail's control: the hue at half strength on a 3% wash, and the mark opens again
		await page.getByTestId('toggle-settled').click();
		const shown = await drawn(m);
		expect(shown.hue).toMatchObject(SUGGESTION);
		expect(shown.hue.a).toBeCloseTo(0.5, 2);
		expect(shown.wash).toMatchObject(SUGGESTION);
		expect(shown.wash.a).toBeCloseTo(0.03, 2);
		await m.click();
		await expect(page.locator('aside.comment-slot.expanded article.box[data-annotation-id="a-2026-09-16-0002"]')).toHaveCount(1);
	});

	test('the session filter hides marks, not only counts', async ({ page }) => {
		// the question is moved into the closed session, which the view hides at rest
		await serve(page, (m) => (m.annotations['a-2026-09-16-0006'].run = QUICK));
		await page.goto('/master/main');
		const m = mark(page, 'a-2026-09-16-0006');
		await expect(m).toHaveClass(/hidden/);
		await expect(m).toContainText('one or two points');
		expect((await drawn(m)).hue.a).toBe(0);
		await m.dispatchEvent('click');
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		// the objection, in the open session, is drawn as before
		await expect(mark(page, 'a-2026-09-16-0001')).not.toHaveClass(/hidden/);
		// admitting closed sessions draws it
		await openPicker(page);
		await page.getByTestId('show-closed').click();
		await page.getByTestId('closed-yes').click();
		await page.keyboard.press('Escape');
		await expect(m).not.toHaveClass(/hidden/);
		expect((await drawn(m)).hue).toMatchObject({ ...QUESTION, a: 1 });
		await m.click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(1);
	});

	test('a displayed formula is ruled beneath, and a block underlined line by line, in the same hue and weight', async ({ page }) => {
		// no fixture annotation marks a display, so the rule is held on the class alone: the same variables draw every shape
		await page.goto('/master/main');
		const vars = await mark(page, 'a-2026-09-16-0001').evaluate((el) => {
			const probe = document.createElement('div');
			probe.className = 'math display annotation-block annotation k-objection s-major';
			el.closest('.fragment')!.append(probe);
			const cs = getComputedStyle(probe);
			const out = { shadow: cs.boxShadow, decoration: cs.textDecorationLine, background: cs.backgroundColor };
			probe.remove();
			return out;
		});
		expect(vars.shadow).toMatch(/rgb\(163, 45, 45\) 0px -3px 0px 0px inset/);
		expect(vars.decoration).toBe('none');
		expect(channels(vars.background).a).toBeCloseTo(0.05, 2);
	});
});

test.describe('marks and boxes', () => {
	test('a node draws no annotation list: its marks open their boxes, show all opens every one that is drawn, in the flow, and the discarded are in its context', async ({ page }) => {
		// a mark opens its annotation as a floating box over the text; `show all annotations` opens every one; nothing below the node lists them again
		await page.goto('/node/sy-0003');
		// counted as "every open annotation on this key has a box", not as a literal, so adding one to the fixture does not fail a test that is about marks and boxes agreeing; a settled one is not drawn and so not opened
		const open = await page.evaluate(async () => {
			const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
			// every key the node owns: its statement and its proofs, which carry ids of their own rather than a `/proof` suffix
			const keys = Object.entries(m.keys)
				.filter(([, k]: [string, any]) => k.node === 'sy-0003')
				.map(([id]) => id);
			return Object.values(m.annotations).filter((a: any) => keys.includes(a.target.key) && !a.in_reply_to && !a.discarded && a.status === 'open' && !a.in).length;
		});
		expect(open).toBeGreaterThan(0);
		await expect(page.getByTestId('annotation-list')).toHaveCount(0);
		// the marks that are drawn: the objection's, and not the resolved suggestion's on the proof
		const marks = page.locator('.fragment mark.annotation:not(.settled)');
		await expect(marks).toHaveCount(open);
		await expect(page.locator('.fragment mark.annotation.settled')).toHaveCount(1);
		await marks.first().click();
		const opened = page.locator('[data-testid="comment-expanded"] article.box');
		await expect(opened).toHaveCount(1);
		await expect(opened.locator('header')).toHaveCount(0); // the box begins with the body
		await expect(opened.locator('article.reply')).toHaveCount(1);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
		// the rail opens every one at once, each at its mark or beside its result's label, in the flow rather than floating
		await page.getByTestId('toggle-annotations').click();
		await expect(opened).toHaveCount(open);
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(0);
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
		// and with them closed, a single mark still floats
		await marks.first().click();
		await expect(page.locator('.comment-slot.expanded.floating')).toHaveCount(1);
		// sy-000A's one annotation is discarded and belongs to a closed session, so two filters hide it and the reader must lift both; closing a session hides its annotations, which is what closing one is for
		await page.goto('/node/sy-000A' + beside('/context/sy-000A'));
		const context = pane(page, 1);
		await expect(context.getByTestId('context')).toBeVisible();
		await expect(context.getByTestId('show-discarded')).toHaveCount(0);
		// the closed section unfolds, and the setting inside it is what admits their annotations
		await openPicker(page);
		await page.getByTestId('show-closed').click();
		await page.getByTestId('closed-yes').click();
		await page.keyboard.press('Escape');
		// a quiet line in the context says how many were discarded, and lists them there as rows: a dot in the kind's hue and a link to the annotation, not its box (annotation study A2)
		await expect(context.getByTestId('show-discarded')).toHaveText('1 discarded — show');
		await context.getByTestId('show-discarded').click();
		const rows = context.getByTestId('discarded-list').locator('li');
		await expect(rows).toHaveCount(1);
		await expect(rows.first().locator('.ann-dot')).toHaveAttribute('aria-label', 'note');
		await expect(rows.first().locator('a')).toHaveAttribute('href', 'quilt:a-2026-09-16-0011');
		await expect(context.getByTestId('discarded-list').locator('article.box')).toHaveCount(0);
	});

	test('floating, a mark opens a box clear of every edge and a second mark a second box; × closes one, Escape or a click away the rest, and hovering opens nothing', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		// any delay a hover could open a box after runs on the page's clock, which the test moves on rather than sleeping
		await page.clock.install();
		await page.goto('/master/main');
		// a fragment is wired once for the default placement and again when the stored preferences arrive, so waiting on the marks is not enough: wait until it is wired for the placement under test
		await page.waitForSelector('.fragment[data-comments-wired="floating"] mark.annotation[data-wired-mark]');
		const first = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		const second = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0006"]');
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

	test('inline, a mark expands its comment beneath its paragraph; clicking away closes it', async ({ page }) => {
		await prefs(page, { comments: 'inline' });
		await page.goto('/master/main');
		await page.waitForSelector('.fragment .env[data-key]');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);

		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
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
		await page.goto('/master/main');
		// a-2026-09-16-0010 lost its anchor, so it is marked on sy-0001's label
		const label = page.locator('.fragment .env[data-key="sy-0001"] > .env-label mark.annotation-label');
		await expect(label).toHaveAttribute('data-annotation', 'a-2026-09-16-0010');
		await label.click();
		const open = page.locator('aside.comment-slot.expanded');
		await expect(open.locator('article.box')).toHaveCount(1);
		expect(await label.evaluate((m) => m.closest('.env-label')?.nextElementSibling?.className ?? '')).toContain('expanded');
	});

	test('e opens every annotation at its mark, and h closes them', async ({ page }) => {
		// the document view draws no buttons for these, so the keys are the whole affordance here
		await page.goto('/master/main');
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

	test('a document carries annotations of its own, and they are read beside it', async ({ page }) => {
		// a remark about the whole paper is not drawn above its title; it is read in what the session did, beside the document
		await page.goto('/master/main' + beside(`/session/${REFEREE}?view=did`));
		await expect(page.getByTestId('document-annotations')).toHaveCount(0);
		const did = page.getByTestId('session-did');
		// found by its id rather than by being first; the list is compact rows, not boxes
		const own = Object.values(manifest.annotations as Record<string, { id: string; body_html: string; target: { key: string } }>).find(
			(a) => a.body_html.includes('which conventions it inherits') && a.target.key === 'drafting/main.tex'
		)!;
		await expect(did.locator(`[id="ann-${own.id}"]`)).toHaveCount(1);
	});
});

// The box begins with the body (book 15.3.1; annotation study fixes 12–17): nothing is said in words that the record already shows, the kind is the stripe's hue, what the kind adds stands at a rule in its hue, and everything an annotation can do happens inside its box.
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

	test('it is titled by its kind and severity in the hue with the × on that line, then the body; no status word, author and date on one line', async ({ page }) => {
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-0001');
		await expect(box.getByTestId('severity')).toHaveCount(0);
		// the title line comes first: the kind and its severity, in its hue, and the × at its right
		expect(await box.evaluate((el) => el.firstElementChild?.className)).toContain('title');
		const kind = box.getByTestId('box-kind');
		await expect(kind).toHaveText('Objection (Major)');
		expect(channels(await css(kind, 'color'))).toMatchObject(OBJECTION);
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
		await expect(who).not.toContainText(/objection|major|open/);
		expect(channels(await css(box, 'border-left-color'))).toMatchObject(OBJECTION);
		await expect(box).toHaveCSS('border-left-width', '3px');
		// no wash of its own: the hue is the stripe and nothing else
		expect(channels(await css(box, 'background-color'))).not.toMatchObject(OBJECTION);
	});

	test('the stripe is the hue of every kind, and the neutral for a note or a kind the viewer has never heard of', async ({ page }) => {
		await serve(page, (m) => (m.annotations['a-2026-09-16-0006'].kind = 'remark'));
		const question = await openBox(page, '/node/sy-0002', 'a-2026-09-16-0006');
		expect(channels(await css(question, 'border-left-color'))).toMatchObject(NEUTRAL);
		await page.keyboard.press('Escape');
		const citation = await openBox(page, '/node/sy-0002', 'a-2026-09-16-0005');
		expect(channels(await css(citation, 'border-left-color'))).toMatchObject(CITATION);
		// a kind that takes no severity is titled by its kind alone
		await expect(citation.getByTestId('box-kind')).toHaveText('Citation');
	});

	test('no quote on an anchored annotation, whose mark is the quote; the quote, italic, on one with no mark of its own', async ({ page }) => {
		const anchored = await openBox(page, '/node/sy-0003', 'a-2026-09-16-0001');
		await expect(anchored.locator('.quote')).toHaveCount(0);
		// a-2026-09-16-0010 lost its anchor, so its box is the only record of the words it was about
		const detached = await openBox(page, '/node/sy-0001', 'a-2026-09-16-0010');
		const quote = detached.locator('.quote');
		await expect(quote).toContainText('an involution');
		await expect(quote).toHaveCSS('font-style', 'italic');
	});

	test("a suggestion's proposal stands at a rule in the suggestion's hue, headed by its placement word, rendered, with the verbatim one link away", async ({ page }) => {
		// the fixture's suggestion is resolved, so it is reopened to be drawn
		await serve(page, (m) => (m.annotations['a-2026-09-16-0002'].status = 'open'));
		const box = await openBox(page, '/node/sy-0004', 'a-2026-09-16-0002');
		const pay = box.getByTestId('payload');
		await expect(pay).toHaveAttribute('data-placement', 'replace');
		await expect(pay.locator('.word')).toHaveText('replace');
		expect(channels(await css(pay.locator('.word'), 'color'))).toMatchObject(SUGGESTION);
		expect(channels(await css(pay, 'border-left-color'))).toMatchObject(SUGGESTION);
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

	test("a citation's work stands at a rule in the citation's hue; accept and reject are its verbs, and once decided the box says so once and they go", async ({ page }) => {
		// the publisher resolves the annotation and leaves a reference note naming it; the manifest served after the write says so
		const id = 'a-2026-09-16-0005';
		let accepted = false;
		await page.route('**/build/manifest.json', async (route) => {
			const m = structuredClone(manifest);
			if (accepted) {
				m.annotations[id].status = 'resolved';
				(m.reference_notes ??= []).push({ work: 'any standard text on group actions', for: ['sy-0002'], from: { session: REFEREE, annotation: id } });
			}
			await route.fulfill({ json: m });
		});
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'discard', 'refs-cite']);
		await page.route('**/_api/refs-cite', (r) => ((accepted = true), r.fulfill({ json: { ok: true, result: 'accepted' } })));
		await page.goto('/node/sy-0002');
		await pickSession(page, REFEREE);
		const box = await openBox(page, '/node/sy-0002', id);
		const work = box.getByTestId('work');
		await expect(work).toContainText('any standard text on group actions');
		expect(channels(await css(work, 'border-left-color'))).toMatchObject(CITATION);
		await expect(box.getByTestId('verb-accept')).toBeVisible();
		await expect(box.getByTestId('verb-reject')).toBeVisible();
		await expect(box.getByTestId('verb-reply')).toBeVisible();
		await expect(box.getByTestId('verb-discard')).toBeVisible();
		await expect(box.getByTestId('verb-resolve')).toHaveCount(0);
		await expect(box.getByTestId('verb-edit')).toHaveCount(0);
		await box.getByTestId('verb-accept').click();
		const after = page.locator(`[data-testid="comment-expanded"] article.box[data-annotation-id="${id}"]`);
		await expect(after.getByTestId('outcome')).toHaveText('· accepted');
		await expect(after.getByTestId('verb-accept')).toHaveCount(0);
		await expect(after.getByTestId('verb-reject')).toHaveCount(0);
		await expect(after).toHaveClass(/settled/);
		// the Library's list still names the suggestion, but links to the box rather than deciding it
		await page.goto('/node/sy-0002' + beside('/context/sy-0002'));
		await expect(pane(page, 1).getByTestId('refnote-open')).toHaveCount(0);
	});

	test('reply, edit and discard open inside the box beneath the meta line, and nothing pops over the text', async ({ page }) => {
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'discard']);
		await prefs(page, { comments: 'inline' });
		const box = await openBox(page, '/node/sy-0003', 'a-2026-09-16-0001');
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

		// an edit starts from the body it supersedes, and keeps the severity to hand
		await row.getByTestId('verb-edit').click();
		await expect(panel.getByTestId('verb-text')).toHaveValue(/parity count/);
		await expect(panel.getByTestId('verb-severity')).toHaveValue('major');
		// a discard takes its reason in the same place
		await row.getByTestId('verb-discard').click();
		await expect(panel.getByTestId('verb-text')).toHaveAttribute('placeholder', /why/);
		await expect(panel.getByTestId('verb-send')).toHaveText('discard');
		await expect(page.getByTestId('verb-more')).toHaveCount(0);
	});

	test('a settled box: the stripe at half strength, the body softened, the outcome said once, and reopen its one verb', async ({ page }) => {
		await writes(page, ['annotate', 'reply', 'resolve', 'edit', 'discard']);
		await page.goto('/node/sy-0004');
		// a-2026-09-16-0002 is resolved: its mark is drawn only once settled annotations are shown
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0002"]');
		await expect(mark).toHaveClass(/settled/);
		await page.getByTestId('toggle-settled').click();
		await mark.click();
		const box = page.locator('[data-testid="comment-expanded"] article.box[data-annotation-id="a-2026-09-16-0002"]');
		await expect(box).toHaveClass(/settled/);
		const stripe = channels(await css(box, 'border-left-color'));
		expect(stripe).toMatchObject(SUGGESTION);
		expect(stripe.a).toBeCloseTo(0.5, 1);
		await expect(box.locator('.body').first()).toHaveCSS('color', 'rgb(95, 94, 90)'); // --ink-soft
		await expect(box.locator(':scope > .meta .who')).toContainText('· resolved');
		await expect(box.locator(':scope > .meta .who')).not.toContainText('resolved · resolved');
		const row = box.locator(':scope > .meta').getByTestId('verb-row');
		await expect(row.getByTestId('verb-reopen')).toBeVisible();
		await expect(row.locator('button')).toHaveCount(1);
	});

	test('travel is two-way: a double-click on a mark lands on its box, and one on the box lands on its mark', async ({ page }) => {
		await page.goto('/master/main');
		const mark = page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]');
		await mark.dblclick();
		const box = page.locator('article.box[data-annotation-id="a-2026-09-16-0001"]');
		await expect(box).toHaveCount(1);
		await expect(box).toHaveClass(/travelled/);
		await expect(page.getByTestId('travel-nowhere')).toHaveCount(0);
		await box.locator('.body').first().dblclick();
		await expect(mark).toHaveClass(/travelled/);
		await expect(box).toHaveCount(1);
	});

	test('beside a comparison a card in the flow is the annotation\'s one box: its mark travels to it rather than opening a second', async ({ page }) => {
		await page.goto('/master/main?review=sy-0001&cause=0');
		const card = page.locator('aside.comment-slot.inline article.box[data-annotation-id="a-2026-09-16-0001"]');
		await expect(card).toHaveCount(1);
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]').click();
		await expect(card).toHaveClass(/travelled/);
		await expect(page.locator('article.box[data-annotation-id="a-2026-09-16-0001"]')).toHaveCount(1);
		await expect(page.locator('aside.comment-slot.expanded')).toHaveCount(0);
	});
});

test.describe('the placement', () => {
	test('the placement is a display setting', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('comments-inline').click();
		await expect(page.locator('html')).toHaveAttribute('data-comments', 'inline');
		await expect(page.locator('aside.comment-slot.gutter')).toHaveCount(0);
	});

	test('changing the placement re-wires the document without typesetting it again', async ({ page }) => {
		await prefs(page, { comments: 'floating' });
		await page.goto('/master/main');
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
		await page.getByTestId('settings-toggle').click();
		await page.getByTestId('comments-inline').click();
		await page.waitForSelector('.fragment[data-comments-wired="inline"]');
		await page.getByTestId('comments-floating').click();
		await page.waitForSelector('.fragment[data-comments-wired="floating"]');
		// a later event rendered: a mark opened after the switch draws its box, so any re-typeset the switch set off has had its turn
		await page.keyboard.press('Escape');
		await page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0001"]').click();
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
		await expect(pane(page, 1).getByTestId('reference-notes')).toBeVisible();
		await pane(page, 0).locator('.fragment mark.annotation').first().click();
		await expect(page.locator('article.box').first()).toBeVisible();
		await expect(page.getByTestId('verb-row')).toHaveCount(0);
		await expect(page.getByTestId('tool-select')).toHaveCount(0);
		await expect(page.getByTestId('verb-accept')).toHaveCount(0);
	});

	test('a verb that needs no panel still shows why it was refused', async ({ page }) => {
		// `resolve` is one click and opens no panel, so its refusal is shown in the box: the viewer's own when nothing is selected, the publisher's once the write reaches it
		await page.route('**/_api', (route) => route.fulfill({ json: { write_api: 1, capabilities: ['annotate', 'reply', 'resolve', 'edit', 'discard'], token: 't' } }));
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

// The composer (book 15.3.10; annotation study fixes 5 and 18–21): the header names the words, the kinds are buttons, severity never moves, the submit is the verb, and × or Escape cancel. Against a mocked write API: what is tested here is the form, not the write, which the write suite holds against the real publisher.
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
		// a box defaults to a note, as a selection does
		await expect(form.getByTestId('note-kind').locator('[aria-pressed="true"]')).toHaveAttribute('data-kind', 'note');
	});

	test('five kinds as buttons in their hues, note by default; severity stands for every kind and takes a press only for the two graded ones; the submit says the kind\'s verb', async ({ page }) => {
		const form = await composeOn(page, 'sy-0003');
		const kinds = form.getByTestId('note-kind');
		const severity = form.getByTestId('note-severity');
		const submit = form.getByTestId('note-submit');
		await expect(kinds.locator('button')).toHaveCount(5);
		await expect(kinds.locator('button')).toHaveText(['objection', 'suggestion', 'question', 'citation', 'note']);
		await expect(kinds.locator('[aria-pressed="true"]')).toHaveAttribute('data-kind', 'note');
		await expect(kinds.locator('[data-kind="objection"]')).toHaveCSS('color', 'rgb(163, 45, 45)');
		await expect(kinds.locator('[data-kind="suggestion"]')).toHaveCSS('color', 'rgb(160, 122, 10)');
		await expect(kinds.locator('[data-kind="question"]')).toHaveCSS('color', 'rgb(24, 95, 165)');
		await expect(kinds.locator('[data-kind="citation"]')).toHaveCSS('color', 'rgb(107, 63, 160)');
		await expect(kinds.locator('[data-kind="note"]')).toHaveCSS('color', 'rgb(111, 109, 102)');
		await expect(submit).toHaveText('Note');
		// severity is present for a note and disabled, at 35%
		await expect(severity.locator('button')).toHaveText(['major', 'moderate', 'minor']);
		for (const s of ['major', 'moderate', 'minor']) await expect(severity.locator(`[data-severity="${s}"]`)).toBeDisabled();
		await expect(severity.locator('[data-severity="major"]')).toHaveCSS('opacity', '0.35');
		await expect(severity.locator('[aria-pressed="true"]')).toHaveCount(0);
		const height = (await form.boundingBox())!.height;
		// one click changes the kind; an objection takes a severity, and the submit follows
		await kinds.locator('[data-kind="objection"]').click();
		await expect(kinds.locator('[aria-pressed="true"]')).toHaveAttribute('data-kind', 'objection');
		await expect(submit).toHaveText('Object');
		await expect(submit).toHaveCSS('background-color', 'rgb(163, 45, 45)');
		for (const s of ['major', 'moderate', 'minor']) await expect(severity.locator(`[data-severity="${s}"]`)).toBeEnabled();
		await expect(severity.locator('[data-severity="major"]')).toHaveCSS('opacity', '1');
		await severity.locator('[data-severity="major"]').click();
		await expect(severity.locator('[aria-pressed="true"]')).toHaveAttribute('data-severity', 'major');
		await kinds.locator('[data-kind="suggestion"]').click();
		await expect(submit).toHaveText('Suggest');
		await expect(severity.locator('[aria-pressed="true"]')).toHaveAttribute('data-severity', 'major');
		// a kind that takes none greys the row and drops the choice; the row stays where it was
		await kinds.locator('[data-kind="question"]').click();
		await expect(submit).toHaveText('Ask');
		await expect(severity.locator('[data-severity="major"]')).toBeDisabled();
		await expect(severity.locator('[aria-pressed="true"]')).toHaveCount(0);
		await kinds.locator('[data-kind="citation"]').click();
		await expect(submit).toHaveText('Cite');
		await expect(submit).toHaveCSS('background-color', 'rgb(107, 63, 160)');
		await kinds.locator('[data-kind="note"]').click();
		await expect(submit).toHaveText('Note');
		expect((await form.boundingBox())!.height).toBe(height);
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

// The settled control (book 15.2.5, 15.3.1): a resolved or discarded annotation is not drawn at rest; the rail's `show settled`, or `s`, draws it faintly for the sitting and on every page, and a fresh visit starts with it off.
test.describe('the settled control', () => {
	const settledMark = (page: Page) => page.locator('.fragment mark.annotation[data-annotation~="a-2026-09-16-0002"]');

	test('on a document it shows and hides the settled marks, and their boxes open only while it is on', async ({ page }) => {
		await page.goto('/master/main');
		const m = settledMark(page);
		await expect(m).toHaveClass(/settled/);
		expect((await drawn(m)).hue.a).toBe(0);
		const control = page.getByTestId('toggle-settled');
		await expect(control).toHaveText('show settled');
		await expect(control).toHaveAttribute('aria-pressed', 'false');
		await control.click();
		await expect(control).toHaveText('hide settled');
		await expect(control).toHaveAttribute('aria-pressed', 'true');
		await expect(page.locator('.fragment').first()).toHaveClass(/show-settled/);
		expect((await drawn(m)).hue).toMatchObject(SUGGESTION);
		expect((await drawn(m)).hue.a).toBeCloseTo(0.5, 2);
		// the resolved citation on the theorem has no quote, so shown it is a mark on the theorem's label
		await expect(page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-0004"]')).toHaveCount(1);
		// show all now opens the settled boxes too
		await page.getByTestId('toggle-annotations').click();
		await expect(page.locator('article.box[data-annotation-id="a-2026-09-16-0002"]')).toBeVisible();
		await control.click();
		await expect(control).toHaveText('show settled');
		expect((await drawn(m)).hue.a).toBe(0);
		await expect(page.locator('article.box[data-annotation-id="a-2026-09-16-0002"]')).toHaveCount(0);
		await expect(page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-0004"]')).toHaveCount(0);
	});

	test('on a node the same control, and the s key beside e and h', async ({ page }) => {
		await page.goto('/node/sy-0004');
		const m = settledMark(page);
		expect((await drawn(m)).hue.a).toBe(0);
		await page.getByTestId('toggle-settled').click();
		await expect(page.getByTestId('toggle-settled')).toHaveText('hide settled');
		expect((await drawn(m)).hue.a).toBeCloseTo(0.5, 2);
		// the key, from inside the document, flips it back and forth
		await page.locator('.fragment').first().focus();
		await page.keyboard.press('s');
		await expect(page.getByTestId('toggle-settled')).toHaveText('show settled');
		expect((await drawn(m)).hue.a).toBe(0);
		await page.keyboard.press('s');
		await expect(page.getByTestId('toggle-settled')).toHaveText('hide settled');
		expect((await drawn(m)).hue.a).toBeCloseTo(0.5, 2);
	});

	test('it is off again on a fresh visit', async ({ page }) => {
		await page.goto('/master/main');
		await page.getByTestId('toggle-settled').click();
		await expect(page.getByTestId('toggle-settled')).toHaveText('hide settled');
		await page.goto('/master/main');
		await expect(page.getByTestId('toggle-settled')).toHaveText('show settled');
		expect((await drawn(settledMark(page))).hue.a).toBe(0);
	});

	test('a link to a settled annotation turns it on and opens the box, a discarded one included', async ({ page }) => {
		// a row in What it did or the Context links a settled annotation by `quilt:`; following it is a request to see it, so the control comes on for the sitting and the box opens, rather than the reader landing on a page where nothing is drawn (15.2.5)
		// the discarded note on sy-000A belongs to the closed session; here it is the open one's, so only the settled control stands between the reader and it
		await serve(page, (m) => (m.annotations['a-2026-09-16-0011'].run = REFEREE));
		await page.goto(`/session/${REFEREE}?view=did`);
		await page.locator('[data-testid="did-row"] a[href="quilt:a-2026-09-16-0002"]').first().click();
		await expect(page.getByTestId('toggle-settled')).toHaveText('hide settled');
		await expect(page.locator('[data-pane="1"] article.box.settled[data-annotation-id="a-2026-09-16-0002"]')).toBeVisible();
		// a discarded annotation with no quote is a label mark only while settled annotations are drawn, and its box opens from it and says it was discarded
		await page.goto('/node/sy-000A');
		const label = page.locator('.fragment mark.annotation-label[data-annotation~="a-2026-09-16-0011"]');
		await expect(label).toHaveCount(0);
		await page.getByTestId('toggle-settled').click();
		await label.click();
		const box = page.locator('article.box[data-annotation-id="a-2026-09-16-0011"]');
		await expect(box).toBeVisible();
		await expect(box.getByTestId('outcome')).toHaveText('· discarded');
	});
});
