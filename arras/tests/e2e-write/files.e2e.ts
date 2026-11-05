// The project's files under a running `loom serve` (plan 0.22.7): an HTML file runs in a frame of the publisher's frames origin, never the viewer's, so its own script cannot reach the write API while its `quilt:` links open in the viewer and its selection is reported to `loom here`; an image and a PDF are shown as files.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '../served';
import { pane } from '../workspace';

test('an HTML file runs in a frame of its own origin: its links open in the viewer, its selection is reported, and its script reaches nothing of the viewer', async ({ page, served }) => {
	await page.goto('/file/notes/page.html');
	const iframe = page.getByTestId('html-frame');
	await expect(iframe).toHaveAttribute('src', /\/notes\/page\.html\?loom-viewer=/);
	expect(new URL((await iframe.getAttribute('src'))!).origin).not.toBe(new URL(served.url).origin);
	const frame = page.frameLocator('[data-testid="html-frame"]');
	await expect(frame.getByRole('heading', { name: 'Gadgets' })).toBeVisible();
	const inside = page.frames().find((f) => f !== page.mainFrame() && f.url().includes('loom-viewer='))!;
	// the page's own script can read neither the token nor anything else the viewer is served
	const reached = await inside.evaluate(async (viewer) => {
		try {
			const r = await fetch(viewer + '/_api');
			return `read ${r.status}`;
		} catch {
			return 'blocked';
		}
	}, served.url);
	expect(reached).toBe('blocked');
	// words selected in it are where the person is, for `loom here`
	await inside.evaluate(() => {
		const p = document.querySelector('p')!;
		const range = document.createRange();
		range.selectNodeContents(p);
		getSelection()!.removeAllRanges();
		getSelection()!.addRange(range);
	});
	await expect
		.poll(() => JSON.parse(served.loom(['here', '--json'])).looking?.selection?.text ?? '', { timeout: 10000 })
		.toContain('A gadget is a widget with a handle');
	// a `quilt:` link in it opens beside the page, as any link in the viewer does
	await frame.getByRole('link', { name: 'the first lemma' }).click();
	await expect(page.getByTestId('pane-1').getByTestId('item-tab').first()).toContainText('sy-0002');
	await expect(page).toHaveURL(/\/file\/notes\/page\.html/);
});

/** The file as it stands in the served copy. */
const onDisk = (root: string, path: string) => readFileSync(join(root, path), 'utf8');

test('a box in a Markdown file is ticked in place: one character of the file changes, the page is not drawn again, and Your Changes does not list it', async ({ page, served }) => {
	await page.goto('/file/notes/intro.md');
	const file = pane(page, 0).getByTestId('file-item');
	const boxes = file.locator('li.task input');
	await expect(boxes).toHaveCount(3);
	await expect(boxes.nth(0)).toBeChecked();
	await expect(boxes.nth(1)).not.toBeChecked();
	await expect(boxes.nth(1)).toBeEnabled();
	// the words have lost their brackets and kept their mathematics
	await expect(file.locator('li.task').nth(1)).not.toContainText('[ ]');
	await expect(file.locator('li.task').nth(1).locator('mjx-container')).toHaveCount(1);
	const before = onDisk(served.root, 'notes/intro.md');
	const drawn = await file.locator('h1').elementHandle();
	const generated = () => page.evaluate(async () => (await (await fetch('/build/manifest.json', { cache: 'no-cache' })).json()).generated as string);
	const start = await generated();
	await boxes.nth(1).click();
	await expect(boxes.nth(1)).toBeChecked();
	await expect.poll(() => onDisk(served.root, 'notes/intro.md')).toBe(before.replace('- [ ] Count', '- [x] Count'));
	// once the publication has reached the page it has not been drawn again, so the mathematics and the place hold
	await expect.poll(generated, { timeout: 10000 }).not.toBe(start);
	await page.waitForTimeout(500);
	expect(await drawn!.evaluate((h) => h.isConnected)).toBe(true);
	await expect(boxes.nth(1)).toBeChecked();
	// the file's own edit stays listed, as this quilt keeps one, and the tick is not listed with it
	const [listed] = JSON.parse(served.loom(['changes', '--json'])).changes.filter((c: { path: string }) => c.path === 'notes/intro.md');
	expect(listed.hunks).toBe(1);
	expect(listed.diff).toContain('+A widget is fixed by its locus, and by nothing else.');
	expect(listed.diff).not.toContain('+- [x] Count');
	// a second click undoes it, and the file is as it was
	await boxes.nth(1).click();
	await expect.poll(() => onDisk(served.root, 'notes/intro.md')).toBe(before);
	await expect(boxes.nth(1)).not.toBeChecked();
	// a reload reads the file
	await boxes.nth(2).click();
	await expect.poll(() => onDisk(served.root, 'notes/intro.md')).toContain('- [x] Draw a widget');
	await page.reload();
	await expect(file.locator('li.task input').nth(2)).toBeChecked();
	// and The Record says what was done
	await page.goto('/review/record/acts');
	await expect(page.getByTestId('history-act').filter({ hasText: 'Ticked a box in intro.md' }).first()).toBeVisible();
});

test('boxes ticked faster than the page is published all land, and none goes back', async ({ page, served }) => {
	await page.goto('/file/notes/intro.md');
	const boxes = pane(page, 0).getByTestId('file-item').locator('li.task input');
	await expect(boxes).toHaveCount(3);
	await boxes.nth(1).click();
	await boxes.nth(2).click();
	await boxes.nth(0).click();
	await expect.poll(() => onDisk(served.root, 'notes/intro.md')).toContain('- [ ] Read the first lemma\n- [x] Count the gadgets with $n$ handles\n- [x] Draw a widget');
	await page.waitForTimeout(3500);
	await expect(boxes.nth(0)).not.toBeChecked();
	await expect(boxes.nth(1)).toBeChecked();
	await expect(boxes.nth(2)).toBeChecked();
});

test('a tick on a line that has changed since the page was drawn is refused, the box goes back and the page says why', async ({ page, served }) => {
	await page.goto('/file/notes/intro.md');
	const file = pane(page, 0).getByTestId('file-item');
	const boxes = file.locator('li.task input');
	await expect(boxes).toHaveCount(3);
	const before = onDisk(served.root, 'notes/intro.md');
	// what a page drawn before an edit would send
	await file.locator('li.task').nth(1).evaluate((li: HTMLElement) => (li.dataset.task = '1:00000000'));
	await boxes.nth(1).click();
	await expect(page.getByTestId('file-tick-refused')).toContainText('changed since the page was drawn');
	await expect(boxes.nth(1)).not.toBeChecked();
	expect(onDisk(served.root, 'notes/intro.md')).toBe(before);
	// the next tick clears it
	await boxes.nth(2).click();
	await expect(page.getByTestId('file-tick-refused')).toHaveCount(0);
	await expect.poll(() => onDisk(served.root, 'notes/intro.md')).toContain('- [x] Draw a widget');
});

test('an HTML file can find and read the project and open what it finds, and cannot write', async ({ page, served }) => {
	writeFileSync(
		join(served.root, 'notes/open.html'),
		`<!doctype html><title>Open</title><body><h1>Open</h1><ul id="list"></ul><p id="write"></p><script>
		(async () => {
			const { files } = await (await fetch('/.loom/files.json')).json();
			const list = document.getElementById('list');
			for (const path of files.filter((f) => f.endsWith('.md'))) {
				const text = await (await fetch('/' + path)).text();
				const open = text.split('\\n').filter((l) => l.startsWith('- [ ] ')).length;
				if (!open) continue;
				const a = document.createElement('a');
				a.href = 'quilt:' + path;
				a.textContent = path + ': ' + open;
				const li = document.createElement('li');
				li.append(a);
				list.append(li);
			}
			const tried = await fetch('/_api/file-tick', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }).catch(() => null);
			document.getElementById('write').textContent = 'write: ' + (tried ? tried.status : 'blocked');
		})();
		</script></body>`
	);
	const manifest = () => page.evaluate(async () => await (await fetch('/build/manifest.json', { cache: 'no-cache' })).text());
	await page.goto('/file/notes/intro.md');
	await expect.poll(manifest, { timeout: 10000 }).toContain('notes/open.html');
	await page.goto('/file/notes/open.html');
	const frame = page.frameLocator('[data-testid="html-frame"]');
	const link = frame.getByRole('link', { name: 'notes/intro.md: 2' });
	await expect(link).toBeVisible();
	await expect(frame.locator('#write')).toHaveText('write: 501');
	await link.click();
	await expect(page.getByTestId('pane-1').getByTestId('file-item').locator('h1')).toHaveText('Notes on the widgets');
});

test('an image and a PDF of the project are shown as files', async ({ page }) => {
	await page.goto('/file/notes/figure.png');
	await expect.poll(() => pane(page, 0).locator('img.file-image').evaluate((i: HTMLImageElement) => i.naturalWidth)).toBe(2);
	await page.goto('/file/drafting/figures/fig.pdf');
	await expect(pane(page, 0).locator('[data-kind="pdf"] canvas').first()).toBeVisible();
});

test.describe('a Markdown file holding HTML', () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ root }) => {
				writeFileSync(
					join(root, 'notes/embedded.md'),
					`# Embedded\n\nA word in <kbd>ordinary</kbd> HTML.\n\n<iframe width="560" height="315" src="https://www.youtube.com/embed/loom-fixture"></iframe>\n\n<img src="no-such-image.png" onerror="fetch('/_api').then((r) => r.json()).then((j) => (window.loomHostile = j.token))">\n\n<script>window.loomHostile = 'script'</script>\n`
				);
			});
		}
	});

	test('is drawn under the real publisher, whose headers leave its frame alone; its script runs nothing, and a publication of something else does not restart its video', async ({ page, served }) => {
		test.slow(); // three publications: the first, another file's, and its own
		await page.route('https://www.youtube.com/embed/**', (route) => route.fulfill({ contentType: 'text/html', body: '<!doctype html><h1 id="player">player</h1>' }));
		await page.goto('/file/notes/embedded.md');
		const body = pane(page, 0).getByTestId('file-item').locator('.file-body');
		await expect(body.locator('kbd')).toHaveText('ordinary');
		const iframe = body.locator('iframe');
		await expect(page.frameLocator('.file-body iframe').locator('#player')).toBeVisible();
		await expect.poll(() => body.locator('img').evaluate((i: HTMLImageElement) => i.complete)).toBe(true);
		expect(await page.evaluate(() => (window as unknown as { loomHostile?: string }).loomHostile)).toBeUndefined();
		await expect(body).toContainText(`<script>window.loomHostile = 'script'</script>`);
		// the body itself is confined as everything under /build/ is, and the viewer reads it all the same
		const answer = await page.request.get(`${served.url}/build/files/notes/embedded.md.html`);
		expect(answer.headers()['content-security-policy']).toBe('sandbox');

		await iframe.evaluate((f: HTMLIFrameElement) => (f.dataset.kept = 'yes'));
		const fetched = page.waitForResponse((r) => r.url().includes('/build/files/notes/embedded.md.html'));
		const intro = join(served.root, 'notes/intro.md');
		writeFileSync(intro, readFileSync(intro, 'utf8') + '\nAnother line.\n');
		await fetched;
		await page.waitForTimeout(100);
		await expect(iframe).toHaveAttribute('data-kept', 'yes');

		writeFileSync(join(served.root, 'notes/embedded.md'), '# Changed\n');
		await expect(body.locator('h1')).toHaveText('Changed');
		await expect(iframe).toHaveCount(0);
	});
});
