// Asking an agent for a work's overview under a running `loom serve` (plan 0.24.3): a person's annotation on the whole work, which an agent hears of as it hears of any annotation a person writes, written whatever session is selected.
import { expect, test } from '../served';

const ASK = 'Read this paper through and write its overview.';

test('Ask an agent writes an annotation on the whole work, with no session selected, and then says it was asked', async ({ page, served }) => {
	await page.goto('/library/Kre99?view=info');
	await expect(page.getByTestId('session-footer-lead')).toHaveText('not writing in a session');
	const empty = page.getByTestId('overview-empty');
	await expect(empty.getByTestId('no-session-tip')).toHaveCount(0);
	await empty.getByTestId('ask-agent').click();
	await expect(empty.getByTestId('ask-agent-asked')).toContainText('asked today');
	await expect(empty.getByTestId('ask-agent')).toHaveText('Ask again');
	await expect(page.getByTestId('status-ask')).toHaveText('Ask again');
	// an annotation on the work itself, no page of it, naming no session
	const made = served.log().filter((e) => e.event === 'created' && e.body === ASK);
	expect(made).toHaveLength(1);
	expect(made[0].page ?? null).toBeNull();
	expect(made[0]).not.toHaveProperty('session');
});
