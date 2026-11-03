// Review as the meta view and notes (plan 0.22.8), read from the fixture: Review leads with what changed in the open files since the author's look, each with its diff; Suggestions lists what waits to be applied; a file's notes stand quietly at its head, a faded one hidden until asked for; and the notes of a session read in its transcript, by time among its messages.
import { expect, test } from '@playwright/test';
import { pane } from '../workspace';

test('Review leads with the changes since the look, each file with its diff, and lists the suggestions to apply', async ({ page }) => {
	await page.goto('/review');
	const changes = page.getByTestId('section-changes');
	await expect(changes).toContainText('Changes');
	await expect(page.getByTestId('section-count-changes')).toHaveText('1');
	await changes.click();
	const change = page.getByTestId('change');
	await expect(change).toHaveCount(1);
	await expect(change).toHaveAttribute('data-path', 'notes/intro.md');
	await expect(change).toContainText('and by nothing else.');
	// the bar says how much changed since when, and stays at the top while the page scrolls
	const bar = page.getByTestId('changes-bar');
	await expect(bar).toContainText('1 file changed since your look');
	await expect(bar).toHaveCSS('position', 'sticky');
	// the file's name opens the file, as the tree does
	await expect(change.getByTestId('change-open')).toHaveAttribute('href', /\/file\/notes\/intro\.md$/);
	// no publisher to ask, so no verbs
	await expect(page.getByTestId('change-keep')).toHaveCount(0);
	await page.getByTestId('section-suggestions').click();
	await expect(page.getByTestId('suggestions')).toBeVisible();
	// a suggestion opens in the document that reads it, at its place, with it open there
	await expect(page.getByTestId('suggestion-open').first()).toHaveAttribute('href', /^\/master\/drafting\/main\?note=a-[\d-]+/);
});

test("a file's notes stand at its head, a faded one hidden until shown", async ({ page }) => {
	await page.goto('/file/notes/intro.md');
	const notes = pane(page, 0).getByTestId('notes-here');
	await expect(notes.locator('summary')).toContainText('1 note');
	await expect(notes.locator('summary')).toContainText('1 faded');
	await notes.locator('summary').click();
	await expect(notes).toContainText('A widget is fixed by its locus');
	await expect(notes).toContainText('kept');
	await notes.getByTestId('notes-faded').click();
	await expect(notes).toContainText('Notes on the widgets');
});

test("a session's notes read in its transcript, by time among its messages", async ({ page }) => {
	await page.goto('/session/s-2026-09-16-0001');
	const transcript = page.getByTestId('transcript');
	await expect(transcript.locator('[data-testid^="noted-"]')).toHaveCount(3);
	await expect(transcript.getByTestId('noted-n-2026-09-16-0001')).toContainText('be a finite widget');
	await expect(transcript.getByTestId('noted-n-2026-09-16-0003')).toContainText('the parity count');
	// the faded one is left out here as everywhere
	await expect(transcript.getByTestId('noted-n-2026-08-20-0001')).toHaveCount(0);
	// a note's link opens what it is on
	await transcript.getByTestId('noted-n-2026-09-16-0002').getByRole('link').click();
	await expect(page.getByTestId('pane-1').getByTestId('item-tab').first()).toContainText('intro.md');
});
