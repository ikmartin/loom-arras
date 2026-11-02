// The project's files (plan 0.22.7): Docs is the project's tree, a directory folding as an explorer's does and remembered so; a Markdown file and a notebook are drawn as the publisher drew them, at the heading a link names; a `.tex` part opens the document that reads it, at its place; an `app:` link asks a publisher, and with none it says so and goes nowhere.
import { expect, test } from '@playwright/test';
import { pane, settings } from '../workspace';

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

test("the agent's documents leave Docs when the reader hides them in Settings, and come back when shown", async ({ page }) => {
	const { serve } = await import('../manifest');
	await serve(page, (m) => {
		const copy = m.masters.find((d: { copy_of?: string }) => d.copy_of)!;
		m.masters = [...m.masters, { ...copy, path: '.loom/copies/old.tex', closed: true }];
	});
	await page.goto('/master/drafting/main');
	const docs = page.getByTestId('docs-part');
	await expect(docs.getByTestId('docs-copies')).toContainText('aidoc');
	await expect(docs.getByTestId('docs-closed')).toBeVisible();
	await settings(page, 'files');
	const hide = page.getByTestId('hide-agent-docs');
	await expect(hide).not.toBeChecked();
	await hide.check();
	await expect(docs.getByTestId('docs-copies')).toHaveCount(0);
	await expect(docs.getByTestId('docs-closed')).toHaveCount(0);
	// the person's own document stays
	await expect(page.getByTestId('docs-tree').getByRole('link', { name: 'main.tex', exact: true })).toBeVisible();
	// remembered in this browser
	await page.reload();
	await expect(docs.getByTestId('docs-copies')).toHaveCount(0);
	await settings(page, 'files');
	await page.getByTestId('hide-agent-docs').uncheck();
	await expect(docs.getByTestId('docs-copies')).toContainText('aidoc');
});
