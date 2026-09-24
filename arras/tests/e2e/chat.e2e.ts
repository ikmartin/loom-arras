// The Chat (plan 0.14 phase 2): a session's conversation and its input in one pane, replacing the Discussion. The transcript comes from the build's pages, and — where a publisher serves — from a poll of `/_api/events`; the status line and the input exist only where a publisher answers (P3). Each test is named for the rule it holds.
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { beside, pane } from '../workspace';
import { openPicker, pickSession } from '../picker';

const manifest = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));
const REFEREE = 's-2026-09-16-0001';
const QUICK = 's-2026-09-15-0001';

type Ev = { seq: number; kind: string; who: string; when: string; body?: string; body_html?: string };

function said(seq: number, who = seq % 2 ? 'A. Author' : 'Referee Agent'): Ev {
	return { seq, kind: 'message', who, when: '2026-09-16T10:00:00Z', body: `message ${seq}`, body_html: `<p>message ${seq}</p>` };
}

/** A transcript of `count` messages, served as the build's pages, with the manifest's count to match. */
async function transcript(page: Page, count: number, id = REFEREE) {
	await page.route('**/build/manifest.json', async (route) => {
		const m = JSON.parse(JSON.stringify(manifest));
		m.sessions.find((s: { id: string }) => s.id === id).seq = count;
		await route.fulfill({ json: m });
	});
	await page.route(`**/build/transcripts/${id}/*.json`, async (route) => {
		const n = Number(route.request().url().match(/\/(\d+)\.json$/)![1]);
		const events: Ev[] = [];
		for (let s = (n - 1) * 100 + 1; s <= Math.min(n * 100, count); s++) events.push(said(s));
		await route.fulfill({ json: { session: id, page: n, events } });
	});
}

/** A publisher that serves messages: the probe, the events poll and the message endpoint. */
async function publisher(page: Page, state: { events: Ev[]; attached: { who: string; kind: string }[] }) {
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message', 'comment'], token: 't' } }));
	await page.route('**/_api/events*', (r) => {
		const since = Number(new URL(r.request().url()).searchParams.get('since') ?? 0);
		const events = state.events.filter((e) => e.seq > since);
		r.fulfill({ json: { session: REFEREE, from: since, seq: state.events.at(-1)?.seq ?? 0, events, attached: state.attached } });
	});
	await page.route('**/_api/message', async (r) => {
		const body = r.request().postDataJSON();
		const seq = (state.events.at(-1)?.seq ?? 0) + 1;
		state.events.push({ seq, kind: 'message', who: 'A. Author', when: '2026-09-16T10:05:00Z', body: body.text, body_html: `<p>${body.text}</p>` });
		r.fulfill({ json: { ok: true, result: `posted to ${REFEREE}`, session: REFEREE, seq, attached: state.attached } });
	});
}

test.describe('the transcript', () => {
	test('the Chat opens on the newest message, with no heading of its own', async ({ page }) => {
		await transcript(page, 40);
		await page.goto('/session/' + REFEREE);
		const chat = page.getByTestId('chat');
		await expect(chat.getByTestId('message-40')).toBeInViewport();
		await expect(chat.getByTestId('message-1')).not.toBeInViewport();
		await expect(chat.locator('h1, h2')).toHaveCount(0);
	});

	test('scrolling to the top loads the page before, and the reader stays where they were', async ({ page }) => {
		await transcript(page, 150);
		await page.goto('/session/' + REFEREE);
		const chat = page.getByTestId('chat');
		await expect(chat.getByTestId('message-150')).toBeInViewport();
		await expect(chat.getByTestId('message-100')).toHaveCount(0); // only the last page, until asked
		// one scroll to the top, as a reader makes it: scrolling to the first message held already reaches it, and a second scroll to 0 after the page came in would undo the place kept
		await chat.locator('.log').evaluate((el) => (el.scrollTop = 0));
		await expect(chat.getByTestId('message-100')).toHaveCount(1);
		// the earlier page went in above, and the message that was at the top is still in view
		await expect(chat.getByTestId('message-101')).toBeInViewport();
	});

	test("a body is rendered, links and mathematics, and the agent's messages carry a rule", async ({ page }) => {
		await page.goto('/session/' + REFEREE);
		const first = page.getByTestId('message-1');
		await expect(first).toContainText('hostile review of the parity theorem');
		await expect(first).toHaveClass(/agent/);
		expect(await first.evaluate((el) => getComputedStyle(el).borderLeftStyle)).toBe('solid');
	});

	test('with no publisher, the Chat is the transcript alone', async ({ page }) => {
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-1')).toBeVisible();
		await expect(page.getByTestId('chat-status')).toHaveCount(0);
		await expect(page.getByTestId('composer')).toHaveCount(0);
	});
});

test.describe('one Chat at a time', () => {
	test('the picker opens the Chat beside, focus stays, and the URL remembers it', async ({ page }) => {
		await page.goto('/node/sy-0003');
		await pickSession(page, REFEREE);
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(pane(page, 0)).toHaveClass(/focused/);
		await expect.poll(() => new URL(page.url()).searchParams.get('beside')).toBe('/session/' + REFEREE);
	});

	test("opening a second session's Chat closes the first, and selects it", async ({ page }) => {
		await page.goto('/node/sy-0003' + beside('/session/' + REFEREE));
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
		await expect(page.getByTestId('session-footer-name')).toHaveText('referee');
		// the second is the fixture's closed session, which the picker lists under Closed
		await openPicker(page);
		await page.getByTestId('show-closed').click();
		await page.getByTestId(`session-${QUICK}`).click();
		await expect(pane(page, 1).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 1).getByRole('tab')).toHaveText('quick');
		await expect(page.getByTestId('session-footer-name')).toHaveText('quick');
	});
});

test.describe('where a publisher serves', () => {
	test('the status line says who is listening, and a sent message arrives from the next poll', async ({ page }) => {
		const state = { events: [said(1, 'Referee Agent')], attached: [{ who: 'Referee Agent', kind: 'agent' }] };
		await publisher(page, state);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Referee Agent is attached');
		await page.getByTestId('composer-text').fill('And the second proof?');
		await page.getByTestId('composer-send').click();
		await expect(page.getByTestId('message-2')).toContainText('And the second proof?');
		await expect(page.getByTestId('chat-status')).toHaveText('sent · Referee Agent is attached');
		// the answer lands without a manifest rebuild, and the send's note gives way to it
		state.events.push({ seq: 3, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:06:00Z', body: 'Not reviewed.', body_html: '<p>Not reviewed.</p>' });
		await expect(page.getByTestId('message-3')).toContainText('Not reviewed.');
		await expect(page.getByTestId('chat-status')).toHaveText('Referee Agent is attached');
		await expect(page.getByTestId('message-3')).toBeInViewport();
	});

	test('with nobody listening, it says the message waits', async ({ page }) => {
		const state = { events: [said(1, 'Referee Agent')], attached: [] };
		await publisher(page, state);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('nobody is attached — messages wait in the inbox');
		await page.getByTestId('composer-text').fill('Hello?');
		await page.keyboard.press('Enter');
		await expect(page.getByTestId('chat-status')).toHaveText('sent · it waits in the inbox');
	});
});

test.describe('packets', () => {
	type Row = { id: string; kind: string; act: string; target: string; work?: string | null; page?: number | null };
	const QUESTION: Row = { id: 'a-2026-09-16-0001', kind: 'question', act: 'created', target: 'sy-0003' };
	const NOTE: Row = { id: 'a-2026-09-16-0004', kind: 'note', act: 'created', target: 'drafting/main.tex' };
	const TEXT = '  a-2026-09-16-0001  question · sy-0003 · created by A. Author\n      "Which orbit?"';

	/** A publisher whose packet holds `rows` until a message carries them. */
	async function packet(page: Page, rows: Row[]) {
		const state = { events: [said(1, 'Referee Agent')], attached: [] as { who: string; kind: string }[], rows: [...rows], posted: [] as unknown[] };
		await publisher(page, state);
		await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: state.rows, text: state.rows.length ? TEXT : '' } }));
		await page.route('**/_api/message', async (r) => {
			const body = r.request().postDataJSON();
			state.posted.push(body);
			const seq = state.events.length + 1;
			const changed = state.rows.map((x) => ({ ...x, by: 'A. Author' }));
			state.events.push({ seq, kind: 'message', who: 'A. Author', when: '2026-09-16T10:05:00Z', ...(body.text ? { body: body.text, body_html: `<p>${body.text}</p>` } : {}), changed } as Ev);
			state.rows = [];
			r.fulfill({ json: { ok: true, result: `posted to ${REFEREE}`, session: REFEREE, seq, attached: [] } });
		});
		return state;
	}

	test('the tray lists what the next message carries, and is not drawn when it holds nothing', async ({ page }) => {
		await packet(page, [QUESTION, NOTE]);
		await page.goto('/session/' + REFEREE);
		const tray = page.getByTestId('packet-tray');
		await expect(tray.getByTestId(`packet-row-${QUESTION.id}`)).toContainText('question');
		await expect(tray.getByTestId(`packet-row-${QUESTION.id}`)).toContainText('Theorem 2.1');
		await expect(tray.getByTestId(`packet-row-${NOTE.id}`)).toContainText('main.tex');
		// the preview is the publisher's own text, verbatim
		await tray.getByTestId('packet-preview-toggle').click();
		expect(await tray.getByTestId('packet-preview').textContent()).toBe(TEXT);
	});

	test('the preview is read whole, however long the transcript above it', async ({ page }) => {
		// the principles check: under a long transcript the tray shrank with the log, and the preview showed one clipped line
		const state = await packet(page, [QUESTION, NOTE]);
		for (let n = 2; n <= 60; n++) state.events.push(said(n, 'Referee Agent'));
		const long = Array.from({ length: 12 }, (_, i) => `      line ${i + 1} of what the agent will read`).join('\n');
		await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: state.rows, text: TEXT + '\n' + long } }));
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('message-60')).toBeAttached();
		const tray = page.getByTestId('packet-tray');
		await tray.getByTestId('packet-preview-toggle').click();
		// as tall as what it holds, up to its cap of 40% of the Chat; past that it scrolls
		const [own, holds, chat] = await tray.evaluate((t) => [t.clientHeight, t.scrollHeight, t.parentElement!.clientHeight]);
		expect(own).toBeGreaterThanOrEqual(Math.min(holds, Math.floor(chat * 0.4)) - 1);
		// and opening it kept the reader at the newest message
		await expect(page.getByTestId('message-60')).toBeInViewport();
	});

	test('with nothing marked there is no tray', async ({ page }) => {
		await packet(page, []);
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toBeVisible();
		await expect(page.getByTestId('packet-tray')).toHaveCount(0);
		await expect(page.getByTestId('composer-send')).toBeDisabled();
	});

	test('a row opens its annotation beside, and the Chat stays', async ({ page }) => {
		await packet(page, [QUESTION]);
		await page.goto('/master/main' + beside('/session/' + REFEREE));
		await pane(page, 1).getByTestId(`packet-row-${QUESTION.id}`).locator('a').click();
		// the note is on sy-0003, which the open main.tex holds: it opens there, with its box (DR-280-ikmartin)
		await expect(pane(page, 0).getByTestId('item-tab')).toHaveCount(1);
		await expect(pane(page, 0).getByTestId('comment-expanded')).toBeVisible();
		await expect(pane(page, 1).getByTestId('chat')).toBeVisible();
	});

	test('a packet goes without words, the tray empties, and the message says what it carried', async ({ page }) => {
		const state = await packet(page, [QUESTION, NOTE]);
		await page.goto('/session/' + REFEREE);
		const send = page.getByTestId('composer-send');
		await expect(page.getByTestId('packet-tray')).toBeVisible();
		await expect(send).toBeEnabled();
		await send.click();
		await expect(page.getByTestId('packet-tray')).toHaveCount(0);
		const sent = page.getByTestId('message-2');
		await expect(sent.getByTestId('message-carried')).toHaveText('carried 1 question, 1 note');
		// no words: the message is who, when, and what it carried
		await expect(sent.locator('.body')).toHaveCount(0);
		expect(state.posted).toEqual([{ text: '', session: REFEREE }]);
	});
});

test.describe('an agent loom starts', () => {
	type Agent = { launch: boolean; name: string; state?: string; error?: string; activity?: string };

	/** A publisher whose events answer carries `agent`, as `loom serve` does. */
	async function starting(page: Page, agent: Agent) {
		const state = { agent, stops: 0 };
		await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message', 'agent-stop'], token: 't' } }));
		await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: [], text: '' } }));
		await page.route('**/_api/events*', (r) =>
			r.fulfill({ json: { session: REFEREE, from: 0, seq: 1, events: [said(1, 'Referee Agent')], attached: [], agent: state.agent } })
		);
		await page.route('**/_api/agent-stop', (r) => {
			state.stops++;
			state.agent = { ...state.agent, state: 'stopped' };
			r.fulfill({ json: { ok: true, result: 'stopped', session: REFEREE } });
		});
		return state;
	}

	test('a running turn says what it last ran, and stop ends it', async ({ page }) => {
		const state = await starting(page, { launch: true, name: 'Claude Agent', state: 'running', activity: 'loom source sy-0003 --closure' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent is working · loom source sy-0003 --closure');
		await page.getByTestId('agent-stop').click();
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent was stopped');
		await expect(page.getByTestId('agent-stop')).toHaveCount(0);
		expect(state.stops).toBe(1);
	});

	test('a failed turn says why, with nothing to stop', async ({ page }) => {
		await starting(page, { launch: true, name: 'Claude Agent', state: 'failed', error: 'claude is not on PATH' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent could not run: claude is not on PATH');
		await expect(page.getByTestId('agent-stop')).toHaveCount(0);
	});

	test('where loom starts agents and none is running, it says sending starts one', async ({ page }) => {
		await starting(page, { launch: true, name: 'Claude Agent' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent starts when you send');
	});

	test('where it does not, the line is who is listening, as before', async ({ page }) => {
		await starting(page, { launch: false, name: '' });
		await page.goto('/session/' + REFEREE);
		await expect(page.getByTestId('chat-status')).toHaveText('nobody is attached — messages wait in the inbox');
	});
});

test('a turn that fails after a send says so, rather than that the agent will start', async ({ page }) => {
	// found by the 0.14 study (F7): the send's own note outranked the turn's failure, so the line said "will start" for ever
	const agent = { launch: true, name: 'Claude Agent' } as Record<string, unknown>;
	await page.route('**/_api', (r) => r.fulfill({ json: { write_api: 1, capabilities: ['message'], token: 't' } }));
	await page.route('**/_api/packet*', (r) => r.fulfill({ json: { session: REFEREE, rows: [], text: '' } }));
	await page.route('**/_api/events*', (r) => r.fulfill({ json: { session: REFEREE, from: 0, seq: 1, events: [said(1, 'Referee Agent')], attached: [], agent } }));
	await page.route('**/_api/message', (r) => {
		Object.assign(agent, { state: 'failed', error: 'Session ID is already in use.', started: new Date(Date.now() + 1000).toISOString().replace(/\.\d{3}Z$/, 'Z') });
		r.fulfill({ json: { ok: true, result: 'posted', session: REFEREE, seq: 2, attached: [] } });
	});
	await page.goto('/session/' + REFEREE);
	await page.getByTestId('composer-text').fill('Hello?');
	await page.getByTestId('composer-send').click();
	await expect(page.getByTestId('chat-status')).toHaveText('Claude Agent could not run: Session ID is already in use.');
});
