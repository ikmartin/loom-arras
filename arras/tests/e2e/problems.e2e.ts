// Review › Problems: the person's own problems first, open and counted; an agent's copy's, the cited works' and every remark folded beneath, each said to be whose it is; problems titled by what is wrong, opened at their place, and filtered in the page. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest, serve } from '../manifest';

type D = { severity: string; code: string; owner?: string; locations: { file: string; line: number }[]; keys: string[] };
const all = manifest.diagnostics as D[];
const yours = all.filter((d) => (d.owner ?? 'person') === 'person' && d.severity !== 'info');

/** A cited work's problem, which the fixture's quilt has none of: a dangling reference in Kre99's digest, mended by digesting it again. */
const inDigest = {
	severity: 'error',
	code: 'dangling-link',
	message: '\\ref{nowhere} names no node or region',
	locations: [{ file: '.loom/digests/Kre99.tex', line: 12 }],
	keys: [],
	owner: 'work',
	fixes: [{ label: 'digest Kre99 again', command: 'loom library update Kre99 --only extract --redo', act: { endpoint: 'library-update', body: { works: ['Kre99'], redo: true, steps: ['extract'] } } }]
};

test("the person's problems come first, open and counted, and the rest folded beneath, each said to be whose it is", async ({ page }) => {
	await serve(page, (m) => void m.diagnostics.push(inDigest as never));
	await page.goto('/review/problems');
	const mine = page.getByTestId('problems-yours');
	await expect(mine.getByTestId('problems-yours-count')).toHaveText(String(yours.length));
	await expect(mine.getByTestId('problem')).toHaveCount(yours.length);
	await expect(mine.getByTestId('problem').first()).toBeVisible();
	for (const part of ['problems-copy', 'problems-works', 'problems-remarks']) await expect(page.getByTestId(part)).not.toHaveAttribute('open');
	await expect(page.getByTestId('problems-copy')).toContainText('Proposed Changes');
	await expect(page.getByTestId('problems-copy').locator('a[href="/review/proposed"]')).toHaveCount(1);
	// a cited work's problems stand under the work, which links to its page; with no publisher, digesting again is a command to copy
	await page.getByTestId('problems-works').locator('summary').first().click();
	const work = page.locator('[data-testid="problem-work"][data-work="Kre99"]');
	await expect(work.locator('a[href="/library/Kre99"]')).toBeVisible();
	await expect(work.getByTestId('digest-again')).toHaveCount(0);
	await expect(work.getByTestId('fix').first()).toBeVisible();
	await expect(work.locator('.command').first()).toHaveText('loom library update Kre99 --only extract --redo');
	// Review's column counts what is the person's alone
	await expect(page.getByTestId('section-count-problems')).toHaveText(String(yours.length));
});

test('a problem is titled by what is wrong, with its code beside it', async ({ page }) => {
	await page.goto('/review/problems');
	const mine = page.getByTestId('problems-yours');
	await expect(mine.locator('[data-testid="problem-group"][data-codes="dangling-link"] .title')).toHaveText('A reference points nowhere');
	await expect(mine.locator('[data-testid="problem-group"][data-codes="duplicate-id"] .title')).toHaveText('Defined twice');
	await expect(mine.locator('[data-testid="problem-group"][data-codes="duplicate-id"] .code')).toHaveText('duplicate-id');
	// errors first
	await expect(mine.getByTestId('problem-group').first()).toHaveClass(/sev-error/);
});

test('a location is a link to its file at its line, and a key opens at its place', async ({ page }) => {
	await page.goto('/review/problems');
	const group = page.locator('[data-testid="problems-yours"] [data-testid="problem-group"][data-codes="missing-include"]');
	const at = group.getByTestId('problem-location').first();
	await expect(at).toHaveText('drafting/main.tex:72');
	await at.click();
	const lines = page.getByTestId('file-lines');
	await expect(lines).toBeVisible();
	await expect(lines.locator('#L72')).toHaveClass(/at/);
	await expect(lines.locator('#L72')).toBeInViewport();
	await page.goto('/review/problems');
	const open = page.locator('[data-testid="problems-yours"] [data-testid="problem-group"][data-codes="duplicate-id"]').getByTestId('problem-open').first();
	await expect(open).toHaveAttribute('href', /^\/(node|master|file)\//);
});

test('the filters stand in the page: severity from the URL, and a search over titles and messages', async ({ page }) => {
	await page.goto('/review/problems?severity=error');
	await expect(page.getByTestId('filter-error')).toHaveAttribute('aria-pressed', 'true');
	const errors = yours.filter((d) => d.severity === 'error');
	await expect(page.getByTestId('problems-yours').getByTestId('problem')).toHaveCount(errors.length);
	await page.getByTestId('filter-error').click();
	await expect(page).toHaveURL(/\/review\/problems$/);
	await page.getByTestId('problem-search').fill('points nowhere');
	await expect(page.getByTestId('problems-yours').getByTestId('problem-group')).toHaveCount(1);
	await page.getByTestId('problem-search').fill('no problem says this');
	await expect(page.getByTestId('problems-none')).toHaveText('None of yours matches these filters.');
	// the column is the column's: the page puts no panel in it
	await expect(page.locator('.page-panel')).toHaveCount(0);
});

test('a code the URL names opens where it is, and the help names no command', async ({ page }) => {
	await page.goto('/review/problems?code=loom%3Auses-missing');
	await expect(page.getByTestId('problems-remarks')).toHaveAttribute('open');
	await expect(page.getByTestId('filter-code')).toBeVisible();
	await expect(page.getByTestId('problems-remarks').getByTestId('problem-group').first()).toHaveAttribute('open');
	await page.getByTestId('help-problems').click();
	await expect(page.getByTestId('help-panel-problems')).toContainText('Your files come first');
	await expect(page.getByTestId('help-panel-problems')).not.toContainText('command line');
});

test('a fix is copied, and the page is read at rest with its bar drawn', async ({ page, context, browserName }) => {
	await page.goto('/review/problems');
	const fix = page.getByTestId('problems-yours').getByTestId('fix').first();
	await expect(fix).toHaveText('copy');
	if (browserName === 'chromium') {
		await context.grantPermissions(['clipboard-read', 'clipboard-write']);
		await fix.click();
		await expect(fix).toHaveText('copied');
		expect((await page.evaluate(() => navigator.clipboard.readText())).length).toBeGreaterThan(0);
	}
	expect(await page.evaluate(() => getComputedStyle(document.documentElement).scrollbarColor)).not.toBe('rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)');
});

test('a work with no paper to read links to its row in the library, where one is filed or stopped being asked for', async ({ page }) => {
	await page.goto('/review/problems');
	const link = page.getByTestId('problems-yours').getByTestId('problem-library').first();
	await expect(link).toHaveText('In the library');
	await expect(link).toHaveAttribute('href', /^\/library\?q=/);
	await link.click();
	await expect(page.getByTestId('library-works')).toBeVisible();
	await expect(page.getByTestId('library-works').locator('tbody tr').first()).toBeVisible();
});
