// Every route renders against the conformance fixture, the manifest is read as the interface says (a version it does not accept, a state or code it has never seen, a new build), and the addresses kept for old links still land. Each feature's own rules are in its file. Each test is named for the rule it holds.
import { expect, test } from '@playwright/test';
import { manifest, REFEREE, serve } from '../manifest';

const routes: [string, string][] = [
	['/node/sy-0003', 'Parity'],
	['/node/sy-0200', 'Results'],
	['/master/drafting/main', 'Widgets, gadgets'],
	['/review', 'Your Changes'],
	['/review/proposed', 'Proposed Changes'],
	['/review/record', 'The Record'],
	['/review/record/sessions', 'The Record'],
	['/review/record/acts', 'The Record'],
	['/review/problems', 'Problems'],
	['/graph', 'Graph'],
	['/threads', 'Threads'],
	['/tags', 'Tags'],
	['/tag/orbits', '#orbits'],
	['/taxa', 'Taxa'],
	['/taxon/lemma', 'Lemma'],
	['/review/library', 'Library'],
	['/loose', 'Not in any document']
];

for (const [path, heading] of routes) {
	test(`route ${path} renders`, async ({ page }) => {
		await page.goto(path);
		// a node draws no heading of its own (the tab names it): its title is in its statement
		if (path.startsWith('/node/')) await expect(page.locator('[data-pane] .fragment').first()).toContainText(heading);
		else await expect(page.locator('main h1').first()).toContainText(heading);
	});
}

test('unknown state labels and codes render generically', async ({ page }) => {
	await serve(page, (m) => {
		m.keys['sy-0003'].state = 'mysterious';
		m.diagnostics.push({ severity: 'info', code: 'other:code', message: 'from another publisher', locations: [], keys: [] });
	});
	// a state loom never told arras about is still said, in the gutter Show ids opens, in its own word
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ ids: true })));
	await page.goto('/node/sy-0003');
	await expect(page.locator('.fragment .node-margin', { hasText: 'mysterious' }).first()).toBeVisible();
	// a code no table names is titled by its message, under its own code
	await page.goto('/review/problems?code=other%3Acode');
	const group = page.locator('[data-testid="problem-group"][data-codes="other:code"]');
	await expect(group.locator('.title')).toHaveText('from another publisher');
	await expect(group.locator('.code')).toBeVisible();
});

test('search finds by id, alias, title, and tag', async ({ page }) => {
	await page.goto('/');
	const data = await page.locator('ninja-keys').evaluate((el) => (el as unknown as { data: { id: string; keywords: string; title: string }[] }).data);
	expect(data.map((d) => d.id)).toContain('sy-0002');
	const keywords = data.map((d) => d.keywords).join(' | ');
	expect(keywords).toContain('def:gadget');
	expect(data.map((d) => d.title).join(' | ')).toContain('Parity');
	expect(keywords).toContain('orbits');
});

test('live reload follows the manifest only', async ({ page }) => {
	let version = 0;
	await page.route('**/build/manifest.json', async (route) => {
		const m = structuredClone(manifest);
		if (version > 0) m.corpus.name = 'Renamed corpus';
		await route.fulfill({ json: m });
	});
	await page.goto('/review');
	const named = page.getByTestId('quilt-name');
	await expect(named).toHaveText(manifest.corpus.name);
	version = 1;
	await expect(named).toHaveText('Renamed corpus');
});

test('a session opens on its Chat, and reads also as what it did', async ({ page }) => {
	await page.goto('/threads');
	await expect(page.getByText('referee').first()).toBeVisible();
	// a session opens on the Chat, one of its two readings
	await page.goto('/session/' + REFEREE);
	const chat = page.getByTestId('chat');
	await expect(chat).toBeVisible();
	await expect(page.getByTestId('tab-chat')).toHaveAttribute('aria-pressed', 'true');
	// the agent's account of the run is in the transcript, and no date is a raw timestamp
	await expect(chat).toContainText('hostile review of the parity theorem');
	await expect(chat).not.toContainText(/\d{4}-\d{2}-\d{2}T/);
	// what it did is the session's log, the comments it made among the commands, and no date raw
	await page.getByTestId('tab-did').click();
	const did = page.getByTestId('session-did');
	await expect(did.getByTestId('did-row').first()).toContainText('loom annotate sy-0003 --quote --kind objection');
	await expect(did.getByTestId('session-said')).toHaveCount(0);
	await expect(did.getByTestId('report-step')).toHaveCount(0);
	await expect(did).not.toContainText(/\d{4}-\d{2}-\d{2}T/);
	await expect.poll(() => new URL(page.url()).searchParams.get('view')).toBe('did');
});
