// The project's files under a running `loom serve` (plan 0.22.7): an HTML file runs in a frame of the publisher's frames origin, never the viewer's, so its own script cannot reach the write API while its `quilt:` links open in the viewer and its selection is reported to `loom here`; an image and a PDF are shown as files.
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

test('an image and a PDF of the project are shown as files', async ({ page }) => {
	await page.goto('/file/notes/figure.png');
	await expect.poll(() => pane(page, 0).locator('img.file-image').evaluate((i: HTMLImageElement) => i.naturalWidth)).toBe(2);
	await page.goto('/file/drafting/figures/fig.pdf');
	await expect(pane(page, 0).locator('[data-kind="pdf"] canvas').first()).toBeVisible();
});
