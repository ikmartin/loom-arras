// The session's two readings, the Library's ledger and its one list, and the hover card through the registry (plan 0.13.3 phase 3). Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane } from '../workspace';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

async function serve(page: Page, edit: (m: typeof manifest) => void) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		edit(m);
		await route.fulfill({ json: m });
	});
}

test.describe('the Library', () => {
	test('the library list has one home', async ({ page }) => {
		await page.goto('/library');
		await expect(page.getByTestId('library-works')).toBeVisible();
		// the route is a ledger, a table of what each work needs, and never a second list of works to navigate by
		await expect(page.locator('main ul a[href*="/library/"]')).toHaveCount(0);
		// the list is the panel's, and it stands beside the ledger rather than being displaced by it
		await expect(page.getByTestId('library-list')).toBeVisible();
		await expect(page.getByTestId('library-list').locator('a[href^="/library/"]').first()).toBeVisible();
	});

	test('the ledger says what needs work', async ({ page }) => {
		await serve(page, (m) => {
			m.references.Kre99.results = { 'Kre99-x': { state: 'proposed' } };
			m.references.Man12.reading = { total: 2, open: 1 };
		});
		await page.goto('/library');
		const filters = page.getByRole('group', { name: 'which works' }).getByRole('button');
		await expect(filters).toHaveText([/^all/, /^needs work/, /^proposed/]);
		await page.getByTestId('show-needs-work').click();
		await expect(page).toHaveURL(/show=needs-work/);
		const rows = page.getByTestId('library-works').locator('tbody tr');
		await expect(rows).toHaveCount(2);
		await expect(page.getByTestId('ledger-Kre99')).toBeVisible();
		await expect(page.getByTestId('open-Man12')).toHaveText('1');
		await page.getByTestId('show-proposed').click();
		await expect(rows).toHaveCount(1);
	});

	test("a work's counts are stated once", async ({ page }) => {
		// the panel says whether a copy is filed, the one thing a click cannot be guessed to give; every count is the ledger's
		await page.goto('/master/main');
		const list = page.getByTestId('library-list');
		await expect(list.locator('.dot').first()).toBeAttached();
		const texts = await list.locator('li').allInnerTexts();
		for (const t of texts.filter((x) => !/ledger|more|nothing/.test(x))) expect(t, t).not.toMatch(/\b\d+p?\s*$/);
	});
});

test.describe('the session', () => {
	test('a session reads as its Chat and as what it did', async ({ page }) => {
		await page.goto('/session/s-2026-09-16-0001');
		const chat = page.getByTestId('chat');
		await expect(chat).toBeVisible();
		// the conversation leads, and the tab is the one place the session is named
		await expect(chat.getByTestId('message-1')).toContainText('hostile review of the parity theorem');
		await expect(chat.locator('h1, h2')).toHaveCount(0);
		const text = await chat.innerText();
		expect(text).not.toMatch(/\d{4}-\d{2}-\d{2}T/);
		// the two readings are the rail's views, as a work's are
		await expect(page.getByTestId('tab-chat')).toHaveAttribute('aria-pressed', 'true');
		await page.getByTestId('tab-did').click();
		await expect(page.getByTestId('session-did')).toBeVisible();
		await expect.poll(() => new URL(page.url()).searchParams.get('view')).toBe('did');
	});

	test('a finding opens its target beside', async ({ page }) => {
		// with nothing showing the mark, the finding's row in what it did opens what it is about in the other pane, and the record stays
		await page.goto('/session/s-2026-09-16-0001?view=did');
		const link = pane(page, 0).getByTestId('did-annotation').first();
		await expect(link).toBeVisible();
		await link.click();
		await expect(pane(page, 1)).toBeVisible();
		await expect(pane(page, 0).getByTestId('session-did')).toBeVisible();
	});
});

test.describe('the hover card', () => {
	test('a link to a kind with no preview opens no card', async ({ page }) => {
		// a document, a context or a session has no small render: nothing is made up in its place (P3)
		await page.goto('/node/sy-0003' + beside('/context/sy-0003'));
		const doc = page.getByTestId('context').getByRole('link', { name: 'main.tex' }).first();
		await doc.hover();
		await page.waitForTimeout(600);
		await expect(page.getByTestId('link-preview')).toHaveCount(0);
	});
});
