// Asking an agent for a work's overview under a running `loom serve` (plan 0.24.3): a person's note on the whole work, in the selected session, which an agent reads as it reads any note a person writes; with no session selected, the control says why instead of writing.
import { expect, test } from '../served';
import { pickSession } from '../picker';

test('with no session selected, Ask an agent says why instead of writing', async ({ page }) => {
	await page.goto('/library/Kre99?view=info');
	const empty = page.getByTestId('overview-empty');
	await expect(empty.getByTestId('ask-agent')).toBeDisabled();
	await expect(empty.getByTestId('no-session-tip')).toContainText('No session selected');
	// the status line keeps the reason to its tooltip, since the overview's own section says it in full
	await expect(page.getByTestId('status-ask')).toHaveAttribute('title', /No session selected/);
	await expect(page.getByTestId('work-status').getByTestId('no-session-tip')).toHaveCount(0);
});

test('Ask an agent writes a note on the whole work, which an agent reads, and then says it was asked', async ({ page, served }) => {
	await page.goto('/library/Kre99?view=info');
	await pickSession(page, served.openSessions().at(-1)!);
	const empty = page.getByTestId('overview-empty');
	await empty.getByTestId('ask-agent').click();
	await expect(empty.getByTestId('ask-agent-asked')).toContainText('asked today');
	await expect(empty.getByTestId('ask-agent')).toHaveText('Ask again');
	await expect(page.getByTestId('status-ask')).toHaveText('Ask again');
	// it is a note on the work itself, no page of it, listed where the work's notes are
	await expect(page.getByTestId('notes-here')).toContainText('1 note');
	const noted = JSON.parse(served.loom(['since', '--as', 'Overview Agent', '--json'])).noted as { target: { citekey?: string }; page?: number; body: string }[];
	const ask = noted.find((n) => n.target.citekey === 'Kre99');
	expect(ask?.body).toBe('Read this paper through and write its overview.');
	expect(ask?.page).toBeUndefined();
});
