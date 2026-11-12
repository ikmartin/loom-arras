// The project's files (plan 0.22.7): Docs is the project's tree, a directory folding as an explorer's does and remembered so; a Markdown file and a notebook are drawn as the publisher drew them, at the heading a link names; a `.tex` part opens the document that reads it, at its place; an `app:` link asks a publisher, and with none it says so and goes nowhere.
import { expect, test } from '@playwright/test';
import { pane, prefs, settings } from '../workspace';

test('Docs is the tree of the project: a directory folds, and stays as it was left', async ({ page }) => {
	await page.goto('/master/drafting/main');
	const tree = page.getByTestId('docs-tree');
	const notes = tree.locator('[data-path="notes"]');
	// the directory holding a live document starts open, another starts folded
	await expect(tree.getByRole('link', { name: 'main.tex', exact: true })).toBeVisible();
	await expect(notes.getByRole('button').first()).toHaveAttribute('aria-expanded', 'false');
	await expect(tree.getByRole('link', { name: 'intro.md' })).toHaveCount(0);
	await notes.getByRole('button').first().click();
	await expect(tree.getByRole('link', { name: 'intro.md' })).toBeVisible();
	await expect(tree.getByRole('link', { name: 'page.html' })).toBeVisible();
	// loom's own directory, and what is hidden, never show
	await expect(tree.getByRole('button', { name: /\.loom/ })).toHaveCount(0);
	await page.reload();
	await expect(tree.getByRole('link', { name: 'intro.md' })).toBeVisible();
	// the research state is listed where it lives, and opens as its page
	await tree.getByTestId('docs-state').getByRole('link').click();
	await expect(page).toHaveURL(/\/page\/state$/);
});

test('a Markdown file is drawn, opened at the heading a link names, and its links are followed in the viewer', async ({ page }) => {
	await page.goto('/file/notes/intro.md#next');
	const file = pane(page, 0).getByTestId('file-item');
	await expect(file.locator('h1')).toHaveText('Notes on the widgets');
	await expect(file.locator('h2#next')).toBeInViewport();
	// an empty link is named by the viewer, and maths is typeset
	await expect(file.locator('a[href="quilt:sy-0002"]')).not.toHaveText('');
	await expect(file.locator('mjx-container').first()).toBeVisible();
	// a relative link to the paper became a link the viewer follows, opened beside the file
	await file.getByRole('link', { name: 'the paper' }).click();
	await expect(page.getByTestId('pane-1').getByTestId('item-tab').first()).toContainText('main.tex');
	await expect(page).toHaveURL(/\/file\/notes\/intro\.md/);
});

test('a box in a Markdown file is drawn but cannot be changed with no publisher to write to', async ({ page }) => {
	await page.goto('/file/notes/intro.md');
	const tasks = pane(page, 0).getByTestId('file-item').locator('li.task');
	await expect(tasks).toHaveCount(3);
	await expect(tasks.nth(0).locator('input')).toBeChecked();
	await expect(tasks.nth(0).locator('input')).toBeDisabled();
	await expect(tasks.nth(1).locator('input')).not.toBeChecked();
	await expect(tasks.nth(1).locator('input')).toBeDisabled();
	await expect(tasks.nth(1)).toHaveText(/^Count the gadgets/);
});

test('Markdown wraps at the line width in a wide window, centred, whatever the format, and fills a narrower pane', async ({ page }) => {
	await page.setViewportSize({ width: 2000, height: 900 });
	const file = pane(page, 0).getByTestId('file-item');
	const body = file.locator('.file-body');
	// the default format is a paper's, whose text block is narrower than any of these: Width alone decides
	for (const [width, rems] of [['narrow', 40], ['mid', 48], ['wide', 56]] as const) {
		await prefs(page, { width });
		await page.goto('/file/notes/intro.md');
		await expect(body.locator('h1')).toBeVisible();
		const rem = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
		const [at, around] = [(await body.boundingBox())!, (await file.boundingBox())!];
		expect(at.width).toBeCloseTo(rems * rem, 0);
		expect(Math.abs(at.x - around.x - (around.x + around.width - at.x - at.width))).toBeLessThanOrEqual(4);
	}
	// a pane narrower than the line is simply filled, up to its padding
	await page.setViewportSize({ width: 600, height: 900 });
	await expect.poll(async () => (await file.boundingBox())!.width - (await body.boundingBox())!.width).toBeLessThanOrEqual(52);
});

test('the research state keeps the same line, the line saying who wrote it standing over the text', async ({ page }) => {
	await page.setViewportSize({ width: 2000, height: 900 });
	await page.goto('/page/state');
	const state = page.getByTestId('research-state');
	const body = state.locator('.body');
	await expect(body).toBeVisible();
	const rem = await page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
	const [at, meta] = [(await body.boundingBox())!, (await state.getByTestId('page-meta').boundingBox())!];
	expect(at.width).toBeCloseTo(48 * rem, 0);
	expect(meta.x).toBeCloseTo(at.x, 0);
});

test('a Markdown file draws the HTML it holds, with Markdown and mathematics working inside it', async ({ page }) => {
	await page.goto('/file/notes/embeds.md');
	const body = pane(page, 0).getByTestId('file-item').locator('.file-body');
	await expect(body.locator('kbd')).toHaveText('ordinary');
	await expect(body.locator('abbr')).toHaveAttribute('title', 'a run of HTML of its own');
	await expect(body.locator('details summary')).toHaveText("A fold of the file's own");
	await expect(body.locator('details em')).toHaveText('emphasis');
	await expect(body.locator('details mjx-container')).toHaveCount(1);
	await expect(body).toContainText('Vector<T> left as a word');
	// its image is found as a Markdown image is, and what it may not ask of the viewer's page is gone
	const line = body.locator('p[align="center"]');
	await expect(line.locator('img')).toHaveAttribute('src', '/_files/notes/figure.png');
	expect(await line.evaluate((p) => p.getAttributeNames())).toEqual(['align']);
});

test('a frame in a Markdown file is drawn inside the column at its own shape, and what it loads reaches nothing of the viewer', async ({ page }) => {
	await page.setViewportSize({ width: 2000, height: 1400 });
	// no network in a test: the player is a page that tries what a hostile one would
	await page.route('https://www.youtube.com/embed/**', (route) =>
		route.fulfill({
			contentType: 'text/html',
			body: `<!doctype html><h1 id="player">player</h1><script>
				let reached = 'nothing';
				try { reached = parent.document.title ? 'the viewer' : 'the viewer'; } catch {}
				document.getElementById('player').dataset.reached = reached;
				try { top.location.href = 'https://www.youtube.com/taken'; } catch {}
			</script>`
		})
	);
	await page.goto('/file/notes/embeds.md');
	const body = pane(page, 0).getByTestId('file-item').locator('.file-body');
	const iframe = body.locator('iframe');
	await expect(iframe).toHaveCount(1);
	// what the file wrote is gone, and what it is given is the publisher's
	await expect(iframe).toHaveAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms allow-presentation');
	await expect(iframe).toHaveAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
	await expect(iframe).toHaveAttribute('allow', 'fullscreen; encrypted-media; picture-in-picture');
	for (const gone of ['srcdoc', 'onload', 'frameborder']) expect(await iframe.getAttribute(gone)).toBeNull();
	const player = page.frameLocator('.file-body iframe').locator('#player');
	await expect(player).toHaveAttribute('data-reached', 'nothing');
	await expect(page).toHaveURL(/\/file\/notes\/embeds\.md/);
	// it asked for 560 by 315: it takes the column's width at that shape
	const shape = async () => {
		const [frame, column] = [(await iframe.boundingBox())!, (await body.boundingBox())!];
		return { frame, column };
	};
	await expect.poll(async () => {
		const { frame, column } = await shape();
		return Math.abs(frame.width - column.width);
	}).toBeLessThanOrEqual(1);
	const { frame, column } = await shape();
	expect(frame.width).toBeGreaterThan(560);
	expect(frame.x).toBeCloseTo(column.x, 0);
	expect(frame.height).toBeCloseTo((frame.width * 315) / 560, 0);
	// in a pane narrower than it asked for, it scales rather than overflowing
	await page.setViewportSize({ width: 500, height: 900 });
	await expect.poll(async () => (await iframe.boundingBox())!.width).toBeLessThan(560);
	const narrow = await shape();
	expect(narrow.frame.x + narrow.frame.width).toBeLessThanOrEqual(narrow.column.x + narrow.column.width + 1);
	expect(narrow.frame.height).toBeCloseTo((narrow.frame.width * 315) / 560, 0);
	expect(await body.evaluate((el) => el.scrollWidth - el.clientWidth)).toBeLessThanOrEqual(0);
});

test('nothing a Markdown file writes runs in the viewer: no script, no handler, no javascript: address', async ({ page }) => {
	await page.goto('/file/notes/embeds.md');
	const body = pane(page, 0).getByTestId('file-item').locator('.file-body');
	// what is refused stays on the page as the text it is
	await expect(body).toContainText(`<script>window.loomHostile = 'script'</script>`);
	await expect(body).toContainText('<iframe src="http://frames.example/plain">');
	await expect(body.locator('mjx-container svg a')).toHaveCount(1);
	const written = await body.evaluate((el) => ({
		scripts: el.querySelectorAll('script').length,
		frames: [...el.querySelectorAll('iframe')].map((f) => f.getAttribute('src')),
		handlers: [...el.querySelectorAll('*')].flatMap((e) => e.getAttributeNames().filter((n) => n.startsWith('on')))
	}));
	expect(written).toEqual({ scripts: 0, frames: ['https://www.youtube.com/embed/loom-fixture'], handlers: [] });
	expect(await body.locator('#by-scheme').getAttribute('href')).toBeNull();
	expect(await body.locator('#by-tab').getAttribute('href')).toBeNull();
	// the image with the handler has failed by now, and each link is clicked as a person would
	await expect.poll(() => body.locator('img[alt="An image with a handler"]').evaluate((i: HTMLImageElement) => i.complete)).toBe(true);
	await body.locator('#by-scheme').click();
	await body.locator('#by-tab').click();
	await body.locator('mjx-container svg a').click();
	await page.waitForTimeout(100);
	// a formula's link reaches the page as written, and a browser reads the scheme past the space it opens with: the viewer does not follow it, in a browser that would run it either
	const followed = await body.locator('mjx-container svg a').evaluate((a) => a.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 })));
	expect(followed).toBe(false);
	expect(await page.evaluate(() => (window as unknown as { loomHostile?: string }).loomHostile)).toBeUndefined();
});

test('a notebook is drawn read-only from its saved cells, an HTML output by its plain form', async ({ page }) => {
	await page.goto('/file/notes/run.ipynb');
	const file = pane(page, 0).getByTestId('file-item');
	await expect(file.locator('h2#counting')).toHaveText('Counting');
	await expect(file.locator('.nb-count')).toHaveText('[1]');
	await expect(file).toContainText('count    3');
	await expect(file.locator('table')).toHaveCount(0);
});

test('a .tex part opens the document that reads it, at its place', async ({ page }) => {
	await page.goto('/master/drafting/main');
	const tree = page.getByTestId('docs-tree');
	await tree.getByRole('button', { name: /sections$/ }).click();
	await tree.getByRole('link', { name: 'results.tex' }).click();
	await expect(page).toHaveURL(/\/master\/drafting\/main#/);
});

test('an app: link with no publisher to ask goes nowhere and says why', async ({ page }) => {
	await page.goto('/file/notes/intro.md');
	const anki = pane(page, 0).getByTestId('file-item').getByRole('link', { name: 'Open Anki' });
	await anki.click();
	await expect(page).toHaveURL(/\/file\/notes\/intro\.md$/);
	await expect(anki).toHaveAttribute('title', /.+/);
});

test("LaTeX's auxiliary files are left out of the tree until the reader asks for them in Settings", async ({ page }) => {
	const { serve } = await import('../manifest');
	await serve(page, (m) => {
		m.files = [...(m.files ?? []), { path: 'drafting/main.aux', kind: 'text', bytes: 10 }, { path: 'drafting/main.synctex.gz', kind: 'other', bytes: 10 }, { path: 'drafting/main.pdf', kind: 'pdf', bytes: 10 }];
	});
	await page.goto('/master/drafting/main');
	const tree = page.getByTestId('docs-tree');
	await expect(tree.getByRole('link', { name: 'main.tex', exact: true })).toBeVisible();
	await expect(tree.getByRole('link', { name: 'main.aux' })).toHaveCount(0);
	await expect(tree.getByRole('link', { name: 'main.synctex.gz' })).toHaveCount(0);
	// the compiled PDF is the document's output, not auxiliary
	await expect(tree.getByRole('link', { name: 'main.pdf' })).toBeVisible();
	await settings(page, 'files');
	const hide = page.getByTestId('hide-aux');
	await expect(hide).toBeChecked();
	await hide.uncheck();
	await expect(tree.getByRole('link', { name: 'main.aux' })).toBeVisible();
	// remembered in this browser
	await page.reload();
	await expect(tree.getByRole('link', { name: 'main.aux' })).toBeVisible();
});

test("the agents' config documents leave the tree when the reader hides them in Settings, and come back when shown", async ({ page }) => {
	const { serve } = await import('../manifest');
	await serve(page, (m) => {
		m.files = [...(m.files ?? []), ...['AGENTS.md', 'CLAUDE.md', 'GEMINI.md', 'notes/CLAUDE.md'].map((path) => ({ path, kind: 'markdown', bytes: 10 }))];
	});
	await page.goto('/master/drafting/main');
	const tree = page.getByTestId('docs-tree');
	await expect(tree.getByRole('link', { name: 'AGENTS.md', exact: true })).toBeVisible();
	await settings(page, 'files');
	const hide = page.getByTestId('hide-agent-config');
	await expect(hide).not.toBeChecked();
	await hide.check();
	for (const name of ['AGENTS.md', 'CLAUDE.md', 'GEMINI.md']) await expect(tree.getByRole('link', { name, exact: true })).toHaveCount(0);
	// the project's other files stay, and so do the agent's copies of a document
	await expect(tree.getByRole('link', { name: 'README.md', exact: true })).toBeVisible();
	await expect(page.getByTestId('docs-copies')).toContainText('aidoc');
	// remembered in this browser
	await page.reload();
	await expect(tree.getByRole('link', { name: 'AGENTS.md', exact: true })).toHaveCount(0);
	await settings(page, 'files');
	await page.getByTestId('hide-agent-config').uncheck();
	await expect(tree.getByRole('link', { name: 'AGENTS.md', exact: true })).toBeVisible();
});

test('the project tree stands under Files, a shelf open by default that folds as Library does', async ({ page }) => {
	await page.goto('/master/drafting/main');
	const files = page.getByTestId('files-toggle');
	await expect(files).toHaveAttribute('aria-expanded', 'true');
	// hovering it says what it is a view of: the project's own directory
	await expect(files).toHaveAttribute('title', 'View of files in synthetic/');
	await expect(page.getByTestId('docs-tree')).toBeVisible();
	// the same kind of control as Library's, above it
	expect(await files.getAttribute('class')).toBe(await page.getByTestId('library-toggle').getAttribute('class'));
	const at = async (id: string) => (await page.getByTestId(id).boundingBox())!.y;
	expect(await at('files-toggle')).toBeLessThan(await at('library-toggle'));
	await files.click();
	await expect(files).toHaveAttribute('aria-expanded', 'false');
	await expect(page.getByTestId('docs-tree')).toHaveCount(0);
	await files.click();
	await expect(page.getByTestId('docs-tree')).toBeVisible();
	// open, the shelf is one box holding its head and the tree, whose top rows start where the head's caret does
	const shelf = page.getByTestId('files-shelf');
	await expect(shelf.getByTestId('files-toggle')).toBeVisible();
	await expect(shelf.getByTestId('docs-tree')).toBeVisible();
	const caret = (await files.locator('.caret').boundingBox())!.x;
	const top = (await page.getByTestId('docs-tree').getByRole('link', { name: 'README.md', exact: true }).boundingBox())!.x;
	expect(Math.abs(top - caret)).toBeLessThanOrEqual(2);
});

test('each row says whether agents edit it too, and the mark says why under the pointer', async ({ page }) => {
	await page.goto('/master/drafting/main');
	// the fixture's deny list is empty, so only what loom always protects is the person's alone
	await expect(page.getByTestId('access-config.toml')).toHaveAttribute('data-agents', 'no');
	await expect(page.getByTestId('access-research-state.md')).toHaveAttribute('data-agents', 'no');
	await expect(page.getByTestId('access-README.md')).toHaveAttribute('data-agents', 'yes');
	await expect(page.getByTestId('access-drafting')).toHaveAttribute('data-agents', 'yes');
	// an agent's copy is one agents edit, whatever the folder of the document it copies
	await expect(page.getByTestId('access-.loom/copies/aidoc.tex')).toHaveAttribute('data-agents', 'yes');
	await page.getByTestId('access-config.toml').hover();
	await expect(page.getByTestId('access-config.toml-says')).toContainText("Only you edit this");
	await expect(page.getByTestId('access-config.toml-says')).toContainText("No agent writes the quilt's configuration.");
	await page.mouse.move(800, 400);
	await expect(page.getByTestId('access-config.toml-says')).toHaveCount(0);
	// a copy's mark names the document its changes go back to
	await page.getByTestId('access-.loom/copies/aidoc.tex').hover();
	await expect(page.getByTestId('access-.loom/copies/aidoc.tex-says')).toContainText('back to main.tex through Review › Proposed Changes');
	// and the copy hangs from that document by a hooked line pointing up into it
	const hook = await page.getByTestId('docs-copies').locator('li').first().evaluate((li) => [getComputedStyle(li, '::before').borderLeftStyle, getComputedStyle(li, '::after').clipPath]);
	expect(hook[0]).toBe('solid');
	expect(hook[1]).toContain('polygon');
});

test("words selected on a project PDF are offered Quote, and let go of take it with them", async ({ page }) => {
	const stream = 'BT /F1 24 Tf 72 700 Td (A gadget is a widget) Tj ET';
	const pdf = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length ${stream.length}>>stream
${stream}
endstream endobj
trailer<</Root 1 0 R>>
%%EOF`;
	const { serve } = await import('../manifest');
	await serve(page, (m) => {
		m.files = [...(m.files ?? []), { path: 'notes/gadgets.pdf', kind: 'pdf', bytes: pdf.length }];
	});
	await page.route('**/_files/notes/gadgets.pdf', (route) => route.fulfill({ body: pdf, contentType: 'application/pdf' }));
	// Quote writes nothing, so it is offered where no publisher takes writes
	await page.goto('/file/notes/gadgets.pdf');
	const words = page.locator('.page .text span').filter({ hasText: 'gadget' }).first();
	await expect(words).toBeVisible();
	// selected as a reader does, with the mouse, which is what offers the chip
	const box = (await words.boundingBox())!;
	await page.mouse.move(box.x + 2, box.y + box.height / 2);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width - 2, box.y + box.height / 2, { steps: 5 });
	await page.mouse.up();
	await expect(page.getByTestId('quote-offer')).toBeVisible();
	await page.evaluate(() => getSelection()!.removeAllRanges());
	await expect(page.getByTestId('quote-offer')).toHaveCount(0);
});

test('a shelf growing long enough to scroll narrows nothing in the column', async ({ page }) => {
	// headless Chromium draws no scrollbars, so the shift itself cannot show here: what is held is that the column keeps the bar's width before there is anything to scroll
	await page.goto('/master/drafting/main');
	expect(await page.getByTestId('docs-part').evaluate((el) => getComputedStyle(el).scrollbarGutter)).toBe('stable');
});
