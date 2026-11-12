// The quilt's settings under a running `loom serve` (plan 0.23): a change waits for Save, Save writes config.toml line by line and keeps the person's comments, a refusal is shown beside the setting it names and writes nothing, and a saved deny list that Claude Code's permission file lags is caught up by Update Claude Code.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '../served';
import { settings } from '../workspace';

const comments = (text: string) => text.split('\n').filter((line) => line.includes('#'));

test('a quilt setting waits for Save, and Save writes config.toml with its comments kept', async ({ page, served }) => {
	const config = join(served.root, 'config.toml');
	const before = readFileSync(config, 'utf8');
	await page.goto('/');
	await settings(page, 'general');
	const name = page.getByTestId('config-quilt.name');
	await name.fill('Renamed in Settings');
	await expect(page.getByTestId('settings-savebar')).toContainText('1 unsaved change to config.toml');
	// a change waits, closed or open, and Revert drops it
	await page.keyboard.press('Escape');
	await page.getByTestId('settings-toggle').click();
	await expect(page.getByTestId('settings-savebar')).toBeVisible();
	await page.getByTestId('settings-revert').click();
	await expect(page.getByTestId('settings-savebar')).toHaveCount(0);
	await expect(name).toHaveValue('The synthetic quilt');
	expect(readFileSync(config, 'utf8')).toBe(before);

	await name.fill('Renamed in Settings');
	await page.getByTestId('settings-save').click();
	await expect(page.getByTestId('settings-savebar')).toHaveCount(0);
	await expect(page.getByTestId('quilt-name')).toHaveText('Renamed in Settings');
	const after = readFileSync(config, 'utf8');
	expect(after).toContain('name = "Renamed in Settings"');
	expect(comments(after)).toEqual(comments(before));

	// a refusal is said beside the setting, and nothing is written
	await page.getByTestId('config-quilt.prefix').fill('s-y');
	await page.getByTestId('settings-save').click();
	await expect(page.getByTestId('setting-quilt.prefix').getByTestId('setting-refused')).toContainText('letters and digits');
	await expect(page.getByTestId('settings-savebar')).toContainText('Nothing was saved');
	expect(readFileSync(config, 'utf8')).toBe(after);
});

test('Settings › Annotations writes the types file whole: a renamed type keeps its id, and a deleted one leaves its annotations looking as they did', async ({ page, served }) => {
	const file = join(served.root, '.loom/annotation-types.toml');
	const manifest = () => JSON.parse(readFileSync(join(served.root, '.loom/build/manifest.json'), 'utf8'));
	const question = (Object.values(manifest().annotations) as { id: string; type: string | null; look: unknown; in_reply_to: string | null }[]).find((a) => a.type === 'question' && !a.in_reply_to)!;
	await page.goto('/node/sy-0002');
	const mark = page.locator(`.fragment mark.annotation[data-annotation~="${question.id}"]`).first();
	const band = () => mark.evaluate((el) => getComputedStyle(el).backgroundColor);
	await expect(mark).toBeVisible();
	const drawn = await band();
	await settings(page, 'annotations');
	const tabs = page.getByTestId('type-tab');
	await tabs.nth(1).click();
	await page.getByTestId('type-name').fill('Idea');
	await tabs.nth(2).click();
	await page.getByTestId('type-delete').click();
	await page.getByTestId('type-delete-yes').click();
	await page.getByTestId('types-save').click();
	await expect.poll(() => readFileSync(file, 'utf8')).toContain('name = "Idea"');
	const written = readFileSync(file, 'utf8');
	expect(written).toContain('id = "suggestion"');
	expect(written).not.toContain('id = "question"');
	await expect.poll(() => manifest().annotation_types.map((t: { name: string }) => t.name)).toEqual(['Revision', 'Idea', 'Note']);
	await expect(tabs).toHaveText([/Revision/, /Idea/, /Note/]);
	// its annotations keep the look they were drawn with, and are untyped now
	expect(manifest().annotations[question.id].look).toEqual(question.look);
	await page.keyboard.press('Escape');
	await expect.poll(band).toBe(drawn);
});

test.describe('the agents boundary', () => {
	test.use({
		prepareQuilt: async ({}, use) => {
			await use(({ loom }) => {
				loom(['ai', 'init']);
			});
		}
	});

	test('a saved deny list that Claude Code lags is said, and Update Claude Code catches it up', async ({ page, served }) => {
		await page.goto('/');
		await settings(page, 'agents');
		await expect(page.getByTestId('agents-stale')).toHaveCount(0);
		await page.getByTestId('deny-pattern').fill('notes/');
		await page.getByTestId('deny-add').click();
		await expect(page.getByTestId('config-agents.deny')).toContainText('notes/');
		await page.getByTestId('settings-save').click();
		await expect(page.getByTestId('agents-stale')).toBeVisible();
		await expect(page.getByTestId('settings-attention')).toBeVisible();
		expect(readFileSync(join(served.root, 'config.toml'), 'utf8')).toContain('deny = ["notes/"]');

		await page.getByTestId('agents-update').click();
		await expect(page.getByTestId('agents-stale')).toHaveCount(0);
		await expect(page.getByTestId('settings-attention')).toHaveCount(0);
		const denied = JSON.parse(readFileSync(join(served.root, '.claude', 'settings.json'), 'utf8')).permissions.deny as string[];
		expect(denied).toContain('Edit(/**/notes/**)');
	});
});

test('the front door chosen in Settings is what the viewer opens on', async ({ page, served }) => {
	await page.goto('/');
	await settings(page, 'documents');
	await page.getByTestId('config-quilt.home').selectOption('notes/intro.md');
	await page.getByTestId('settings-save').click();
	await expect(page.getByTestId('settings-savebar')).toHaveCount(0);
	expect(readFileSync(join(served.root, 'config.toml'), 'utf8')).toContain('home = "notes/intro.md"');
	// a browser that remembers no place opens on it
	await page.evaluate(() => localStorage.clear());
	await page.goto('/');
	await expect(page).toHaveURL(/\/file\/notes\/intro\.md/);
});
