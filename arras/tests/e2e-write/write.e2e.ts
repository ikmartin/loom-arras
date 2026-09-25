// Writing from the viewer, against a publisher that is actually serving the write API.
import { expect, test, type Served } from '../served';
import { openPicker, pickSession } from '../picker';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

/**
 * Select the quilt's newest open session, because a write names one (plan 0.13.1) and nothing is selected at rest; returns its id.
 *
 * This is the setup the interface asks of a reader too: the composer is greyed until an open session is chosen, and nothing is opened behind their back.
 */
async function intoASession(page: import('@playwright/test').Page, served: Served): Promise<string> {
	const id = served.openSessions().at(-1)!;
	await pickSession(page, id);
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', /^annotations are written into/);
	return id;
}

/** Select an element's words as a reader would, and let go: the page offers to annotate them. */
async function select(at: import('@playwright/test').Locator): Promise<void> {
	await at.evaluate((node) => {
		const range = document.createRange();
		range.selectNodeContents(node);
		const sel = window.getSelection();
		sel?.removeAllRanges();
		sel?.addRange(range);
		node.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
	});
}

test('a comment written from a selection lands in the log as a person, anchored across the formula it crosses', async ({ page, served }) => {
	// The gate of plan 0.11 Part H, with the tools a work's pages have (phase 4): not "the button appeared" -- the file changed.
	await page.goto('/node/sy-0003');
	await intoASession(page, served);
	const statement = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await statement.locator('mjx-container').first().waitFor();
	await select(statement);
	await page.getByTestId('annotate-offer').click();
	// the header names the words, then the place as the tab names it (this corpus is not compiled, so by its id); the quote carries the formula as TeX
	await expect(page.getByTestId('note-where')).toContainText('finite widget');
	await expect(page.getByTestId('note-where')).toContainText('in sy-0003');
	// the selection stays lit while the comment is written, and the composer does not repeat it
	await expect(page.getByTestId('note-quote')).toHaveCount(0);
	await expect.poll(() => page.evaluate(() => [...((CSS as unknown as { highlights: Map<string, { values(): Iterable<Range> }> }).highlights.get('note-pending')?.values() ?? [])].map((r) => r.toString()).join(' '))).toContain('widget');
	await page.getByTestId('note-body').fill('Does finiteness do any work in the closedness half?');
	// an objection, because severity grades a fault and only `objection` and `suggestion` claim one (DR-204)
	await page.getByTestId('note-kind').locator('[data-kind="objection"]').click();
	await page.getByTestId('note-severity').locator('[data-severity="minor"]').click();
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);

	const mine = served.log().filter((e) => String(e.body ?? '').startsWith('Does finiteness'));
	expect(mine).toHaveLength(1);
	expect(mine[0].kind).toBe('human'); // written by a person, not by the run whose page it was
	expect(mine[0].target).toBe('sy-0003');
	expect(mine[0].annotation_kind).toBe('objection');
	expect(mine[0].severity).toBe('minor');
	// anchored to the sentence, not to the node, and recorded as the source has it: the formula's own TeX
	const exact = (mine[0].anchor as { exact: string }).exact;
	expect(exact).toContain('finite widget');
	expect(exact).toMatch(/\$|\\\(/);
});

test("the publisher's refusal is shown rather than swallowed, and the whole result is offered instead", async ({ page, served }) => {
	// "quote not found" means something different from "no such key", and a reader told only "failed" has to guess.
	await page.goto('/node/sy-0003');
	await intoASession(page, served);
	const statement = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await statement.locator('mjx-container').first().waitFor();
	// words that are nowhere in the source: what a reader would get from a selection loom cannot map back
	await statement.evaluate((p) => p.insertAdjacentText('afterbegin', 'a phrase that appears nowhere in this statement at all '));
	await select(statement);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('This should be refused.');
	await page.getByTestId('note-submit').click();
	const said = page.getByTestId('note-said');
	await expect(said).toContainText('quote');
	expect(served.log().filter((e) => e.body === 'This should be refused.')).toHaveLength(0);
	// nothing is filed as anchored that is not: the one way on is a note on the whole result, said as such
	await page.getByTestId('note-whole').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const whole = served.log().filter((e) => e.body === 'This should be refused.');
	expect(whole).toHaveLength(1);
	expect(whole[0].target).toBe('sy-0003');
	expect(whole[0].anchor ?? null).toBeNull();
});

test('a box drawn round an equation notes the equation itself', async ({ page, served }) => {
	await page.goto('/node/sy-0001');
	await intoASession(page, served);
	const display = page.locator('[data-pane="0"] .fragment .math.display[data-label="eq:fix"]');
	await display.locator('mjx-container').waitFor();
	await page.getByTestId('tool-box').click();
	const b = (await display.boundingBox())!;
	await page.mouse.move(b.x + 4, b.y + 2);
	await page.mouse.down();
	await page.mouse.move(b.x + b.width - 4, b.y + b.height - 2, { steps: 6 });
	await page.mouse.up();
	await expect(page.getByTestId('note-where')).toContainText('equation');
	await page.getByTestId('note-body').fill('Name the fixed locus here.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const mine = served.log().filter((e) => e.body === 'Name the fixed locus here.');
	expect(mine).toHaveLength(1);
	expect(mine[0].target).toBe('sy-0001#eq:fix');
	// and once the publisher has rebuilt, the display is marked, underlined rather than barred
	await expect(display).toHaveClass(/annotation-block/, { timeout: 10000 });
	expect(await display.evaluate((d) => getComputedStyle(d).borderLeftWidth)).toBe('0px');
});

test('a document is written on the same way, and what is written there is filed with the document: marked in it, and on no other page', async ({ page, served }) => {
	// decision 9 and 11 of the annotation study: the viewer implies `in` from where the reader is, so a claim made while reading main.tex is about sy-0008 as read there, and talk.tex, which also holds sy-0008, and the node's own page carry no mark for it
	await page.goto('/master/main');
	await intoASession(page, served);
	await expect(page.getByTestId('tool-select')).toBeVisible();
	const words = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0008"] > p[data-src]').first();
	await words.scrollIntoViewIfNeeded();
	await select(words);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('A gadget wants an example.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const mine = served.log().filter((e) => e.body === 'A gadget wants an example.');
	expect(mine).toHaveLength(1);
	expect(mine[0].target).toBe('sy-0008');
	expect(mine[0].in).toBe('drafting/main.tex');
	const id = mine[0].id as string;
	const markOf = () => page.locator(`[data-pane="0"] .fragment mark.annotation[data-annotation~="${id}"]`);
	await expect(markOf()).toHaveCount(1, { timeout: 15000 });
	await page.goto('/master/talk');
	await expect(page.locator('[data-pane="0"] .fragment .env[data-id="sy-0008"]')).toBeVisible();
	await expect(markOf()).toHaveCount(0);
	await page.goto('/node/sy-0008');
	await expect(page.locator('[data-pane="0"] .fragment .env[data-id="sy-0008"]')).toBeVisible();
	await expect(markOf()).toHaveCount(0);
});

test('an annotation written on the node\'s own page is filed with no document', async ({ page, served }) => {
	await page.goto('/node/sy-0008');
	await intoASession(page, served);
	const words = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0008"] > p[data-src]').first();
	await select(words);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('Everywhere a gadget is read.');
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const mine = served.written('Everywhere a gadget is read.');
	expect(mine.target).toBe('sy-0008');
	expect(mine.in ?? null).toBeNull();
});

/** The served quilt's open citation suggestion on sy-0002, by the id the log gave it. */
function citationOn(served: Served): string {
	return served.log().find((e) => e.event === 'created' && e.target === 'sy-0002' && e.annotation_kind === 'citation')!.id as string;
}

/** Open the box of the annotation `id` from its mark on the node page. */
async function boxOf(page: import('@playwright/test').Page, id: string) {
	await page.locator(`[data-pane="0"] .fragment .annotation[data-annotation~="${id}"]`).first().click();
	const box = page.locator(`[data-testid="comment-expanded"] article.box[data-annotation-id="${id}"]`);
	await expect(box).toHaveCount(1);
	return box;
}

test('a citation suggestion is accepted from its box, which then says so, and leaves a breadcrumb', async ({ page, served }) => {
	const id = citationOn(served);
	await page.goto('/node/sy-0002');
	await intoASession(page, served);
	const box = await boxOf(page, id);
	await expect(box.getByTestId('work')).toBeVisible();
	await box.getByTestId('verb-accept').click();
	// the publisher resolves it and notes the work; the box re-read from the next manifest says so once and offers neither verb again
	await expect(box.getByTestId('outcome')).toHaveText('· accepted', { timeout: 15000 });
	await expect(box.getByTestId('verb-accept')).toHaveCount(0);
	await expect(box.getByTestId('verb-reject')).toHaveCount(0);
	const written = readFileSync(join(served.root, 'reference-notes.jsonl'), 'utf8');
	expect(written).toContain('a textbook reference would do');
	expect(written).toContain('"verified": false'); // never a second source of identity truth
	expect(served.log().filter((e) => e.event === 'resolved' && e.id === id)).toHaveLength(1);
	// the context's list still names it as a suggestion no longer open: nothing there decides it
	await page.getByTestId('open-context').click();
	await expect(page.getByTestId('context').getByTestId('refnote-open')).toHaveCount(0);
});

test('a citation suggestion is rejected from its box, which resolves it and notes no work', async ({ page, served }) => {
	const id = citationOn(served);
	await page.goto('/node/sy-0002');
	await intoASession(page, served);
	const box = await boxOf(page, id);
	await box.getByTestId('verb-reject').click();
	await expect(box.getByTestId('outcome')).toHaveText('· rejected', { timeout: 15000 });
	await expect(box.getByTestId('verb-accept')).toHaveCount(0);
	await expect(box.getByTestId('verb-reopen')).toBeVisible();
	const resolved = served.log().filter((e) => e.event === 'resolved' && e.id === id);
	expect(resolved).toHaveLength(1);
	expect(existsSync(join(served.root, 'reference-notes.jsonl')) ? readFileSync(join(served.root, 'reference-notes.jsonl'), 'utf8') : '').not.toContain('a textbook reference would do');
});

/** Comments shown in place (`inline` beneath the block, `floating` at the mark), with the reply written inside the box that is showing them. */
function inPlace(where: 'inline' | 'floating') {
	return async ({ page, served }: { page: import('@playwright/test').Page; served: Served }) => {
		await page.addInitScript(
			(c) => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: c })),
			where
		);
		// the mark this test opens is one the fixture carries, so a fresh copy has it before anything is written
		await page.goto('/node/sy-0003');
		await intoASession(page, served);
		const mark = page.locator('.fragment mark.annotation').first();
		await mark.waitFor();
		const box = page.locator('[data-testid="comment-expanded"]'); // one host, however many comments the mark carries
		await mark.click();
		await expect(box).toHaveCount(1);

		const body = `a reply written in the ${where} box`;
		await page.locator('[data-testid="comment-expanded"] [data-testid="verb-reply"]').first().click();
		await page.locator('[data-testid="comment-expanded"] [data-testid="verb-text"]').first().fill(body);
		// the viewer asks for the manifest once a second; a re-wire on any answer after a write once closed the box
		const polls = (n: number) => {
			let seen = 0;
			return page.waitForResponse((r) => new URL(r.url()).pathname === '/build/manifest.json' && r.status() < 400 && ++seen >= n);
		};
		const afterWrite = polls(3);
		await page.locator('[data-testid="comment-expanded"] [data-testid="verb-send"]').first().click();

		// The write changes the manifest, and the re-wire that follows it must leave the box where the reply was written open, now showing the reply.
		await expect(page.locator('[data-testid="comment-expanded"] .reply').filter({ hasText: body })).toHaveCount(1);
		await afterWrite;
		await expect(box).toHaveCount(1);
		expect(served.log().filter((e) => e.body === body)).toHaveLength(1);

		// And the mark still toggles: one click closes it, the next opens it, and it stays open.
		await mark.click();
		await expect(box).toHaveCount(0);
		await mark.click();
		await expect(box).toHaveCount(1);
		// the pointer's own beat falls inside the click and must not shut what the click opened, nor the next poll's re-wire
		await polls(1);
		await expect(box).toHaveCount(1);
	};
}

test('a reply written in an inline comment box leaves the box open', inPlace('inline'));
test('a reply written in a floating comment box leaves the box open', inPlace('floating'));

test("the Chat posts through the publisher, and the agent's answer arrives without a rebuild", async ({ page, served }) => {
	// plan 0.14 phase 2: the person writes in the Chat, the agent answers with `loom session say` from its own shell, and the answer is read from `/_api/events` rather than waiting for the manifest
	await page.goto('/node/sy-0003');
	const sid = await intoASession(page, served);
	const chat = page.locator('[data-pane="1"]').getByTestId('chat');
	await expect(chat).toBeVisible();
	await chat.getByTestId('composer-text').fill('Is the second proof needed?');
	await chat.getByTestId('composer-send').click();
	await expect(chat.getByTestId('transcript')).toContainText('Is the second proof needed?');
	await expect(chat.getByTestId('chat-status')).toContainText('sent');
	served.loom(['session', 'say', 'Only for the *odd* case.', '--session', sid, '--as', 'Referee Agent'], { AI_AGENT: '1' });
	await expect(chat.getByTestId('transcript')).toContainText('Only for the odd case.', { timeout: 3000 });
	await expect(chat.getByTestId('transcript').locator('em', { hasText: 'odd' })).toHaveCount(1);
});

test('what the person marks goes with their next message, whole, and the agent is handed it', async ({ page, served }) => {
	// plan 0.14 phase 4: a note written in the document waits in the Chat's tray, goes without words, and reaches a parked agent with its body and the words it is on
	await page.goto('/node/sy-0003');
	const sid = await intoASession(page, served);
	const chat = page.locator('[data-pane="1"]').getByTestId('chat');
	await expect(chat).toBeVisible();
	const statement = page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first();
	await statement.locator('mjx-container').first().waitFor();
	await select(statement);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill('Packet: does the fixed point count once?');
	await page.getByTestId('note-kind').locator('[data-kind="question"]').click();
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
	const id = served.written('Packet: does the fixed point count once?').id as string;
	await expect(chat.getByTestId(`packet-row-${id}`)).toBeVisible();
	await chat.getByTestId('composer-send').click();
	await expect(chat.getByTestId('packet-tray')).toHaveCount(0);
	await expect(chat.getByTestId('message-carried').last()).toContainText('1 question');
	const out = served.loom(['session', 'next', '--wait', '0', '--json', '--since', '0', '--session', sid, '--as', 'Test Agent'], { AI_AGENT: '1' });
	const carried = JSON.parse(out).events.flatMap((e: { changed?: { id: string; body: string; quote?: string }[] }) => e.changed ?? []);
	const mine = carried.find((c: { id: string }) => c.id === id);
	expect(mine.body).toBe('Packet: does the fixed point count once?');
	expect(mine.quote).toContain('finite widget');
});

/**
 * Turn launching on in the copy, with a stand-in agent that reads the waiting message, sleeps `sleep` seconds and answers `echo: <message>`.
 *
 * Written after the server started: `loom serve` reads the agent configuration when a message waits, not at startup.
 */
function launching(served: Served, sleep: number): void {
	writeFileSync(
		join(served.root, '.fake-agent.py'),
		[
			'import json, subprocess, sys, time',
			'session = sys.argv[1]',
			'loom = [sys.executable, "-m", "loom"]',
			'out = subprocess.run(loom + ["session", "next", "--wait", "0", "--json", "--session", session, "--as", "Stand-in Agent"], capture_output=True, text=True, check=True).stdout',
			'said = [e.get("body", "") for e in json.loads(out)["events"]]',
			`time.sleep(${sleep})`,
			'subprocess.run(loom + ["session", "say", "echo: " + (said[-1] if said else ""), "--session", session, "--as", "Stand-in Agent"], check=True)'
		].join('\n')
	);
	const python = new URL('../../../loom/.venv/bin/python', import.meta.url).pathname;
	mkdirSync(join(served.root, 'ai'), { recursive: true });
	writeFileSync(join(served.root, 'ai/ai-config.toml'), `name = "Stand-in Agent"\nstart = ${JSON.stringify([python, '.fake-agent.py', '{session}'])}\n`);
	const cfgPath = join(served.root, 'config.toml');
	const before = readFileSync(cfgPath, 'utf8');
	const on = /^launch\s*=/m.test(before)
		? before.replace(/^launch\s*=.*$/m, 'launch = true')
		: /^\[ai\]/m.test(before)
			? before.replace(/^\[ai\]\s*$/m, '[ai]\nlaunch = true')
			: before + '\n[ai]\nlaunch = true\n';
	writeFileSync(cfgPath, on);
}

/** The state of the last agent turn loom recorded for a session. */
function agentState(served: Served, sid: string): string {
	return JSON.parse(readFileSync(join(served.root, '.loom/sessions', sid, 'agent.json'), 'utf8')).state;
}

test('with launching on, a message starts the configured agent for a turn, and its answer arrives', async ({ page, served }) => {
	// plan 0.14 phase 5: `loom serve` runs the command in ai/ai-config.toml -- here a stand-in agent -- when a message waits and nobody is listening
	launching(served, 2);
	await page.goto('/node/sy-0003');
	const sid = await intoASession(page, served);
	const chat = page.locator('[data-pane="1"]').getByTestId('chat');
	await chat.getByTestId('composer-text').fill('Stand-in, are you there?');
	await chat.getByTestId('composer-send').click();
	await expect(chat.getByTestId('chat-status')).toContainText('Stand-in Agent is working', { timeout: 10000 });
	await expect(chat.getByTestId('transcript')).toContainText('echo: Stand-in, are you there?', { timeout: 15000 });
	await expect.poll(() => agentState(served, sid), { timeout: 10000 }).toBe('done');
});

test('stopping a launched turn ends it, and loom records the turn stopped', async ({ page, served }) => {
	// the stand-in sleeps long enough that only the stop can end its turn
	launching(served, 60);
	await page.goto('/node/sy-0003');
	const sid = await intoASession(page, served);
	const chat = page.locator('[data-pane="1"]').getByTestId('chat');
	await chat.getByTestId('composer-text').fill('Stand-in, take your time.');
	await chat.getByTestId('composer-send').click();
	await expect(chat.getByTestId('chat-status')).toContainText('Stand-in Agent is working', { timeout: 10000 });
	await expect.poll(() => agentState(served, sid), { timeout: 10000 }).toBe('running');
	await chat.getByTestId('agent-stop').click();
	await expect.poll(() => agentState(served, sid), { timeout: 10000 }).toBe('stopped');
	await expect(chat.getByTestId('agent-stop')).toHaveCount(0);
	await expect(chat.getByTestId('chat-status')).not.toContainText('is working');
});

/** Read the copy's session index. */
function sessionIndex(served: Served): Record<string, unknown>[] {
	return readFileSync(join(served.root, '.loom/sessions/index.jsonl'), 'utf8')
		.split('\n')
		.filter((l) => l.trim())
		.map((l) => JSON.parse(l));
}

/** Select an element's words and write a note on them from the composer. */
async function noteOn(page: import('@playwright/test').Page, at: import('@playwright/test').Locator, body: string): Promise<void> {
	await at.locator('mjx-container').first().waitFor();
	await select(at);
	await page.getByTestId('annotate-offer').click();
	await page.getByTestId('note-body').fill(body);
	await page.getByTestId('note-submit').click();
	await expect(page.getByTestId('note-at')).toHaveCount(0);
}

test('a note lands in the session selected in the viewer, not in the one opened most recently', async ({ page, served }) => {
	// plan 0.13.1 Part 6: the write names the reader's selection; the publisher's own pointer is not consulted
	const [older] = served.openSessions();
	await served.api('session-new', { title: 'later sitting' });
	const newer = served.openSessions().at(-1)!;
	expect(newer).not.toBe(older);
	// the newer one is where a pointer would send it: the most recent, and the one `.loom/sessions/active` names
	expect(readFileSync(join(served.root, '.loom/sessions/active'), 'utf8').trim()).toBe(newer);
	await page.goto('/node/sy-0003');
	await pickSession(page, older);
	await expect(page.getByTestId('session-footer')).toHaveAttribute('aria-label', 'annotations are written into referee');
	await noteOn(page, page.locator('[data-pane="0"] .fragment .env[data-id="sy-0003"] > p[data-src]').first(), 'Which sitting is this in?');
	const mine = served.written('Which sitting is this in?');
	expect(mine.session).toBe(older);
	expect(mine.session).not.toBe(newer);
});

test('an annotation is edited, discarded with a reason and put back, each an event in the log', async ({ page, served }) => {
	// 15.3.4a: edit restates, discard withdraws, and undo is another event rather than the removal of one (DR-174)
	await page.addInitScript(() => localStorage.setItem('arras.prefs', JSON.stringify({ shell: 'c', face: 'serif', size: 'm', width: 'mid', theme: 'light', comments: 'inline' })));
	const id = served.log().find((e) => e.event === 'created' && e.target === 'sy-0003' && e.annotation_kind === 'objection')!.id as string;
	await page.goto('/node/sy-0003');
	const sid = await intoASession(page, served);
	const mark = page.locator(`[data-pane="0"] .fragment mark.annotation[data-annotation~="${id}"]`).first();
	await mark.click();
	const box = page.locator(`[data-testid="comment-expanded"] article.box[data-annotation-id="${id}"]`);
	const head = box.locator(':scope > .meta');
	await expect(box).toHaveCount(1);

	const restated = 'Finiteness is used in the parity count; state it as a hypothesis.';
	await head.getByTestId('verb-edit').click();
	await box.getByTestId('verb-text').fill(restated);
	await box.getByTestId('verb-send').click();
	await expect(box.getByTestId('verb-panel')).toHaveCount(0);
	await expect(box).toContainText(restated);
	const edited = served.log().filter((e) => e.event === 'edited' && e.id === id);
	expect(edited).toHaveLength(1);
	expect(edited[0].body).toBe(restated);
	expect(edited[0].session).toBe(sid);
	expect(edited[0].kind).toBe('human');

	await head.getByTestId('verb-discard').click();
	await box.getByTestId('verb-text').fill('raised in error');
	await box.getByTestId('verb-send').click();
	await expect.poll(() => served.log().filter((e) => e.event === 'discarded' && e.id === id).length).toBe(1);
	const discarded = served.log().filter((e) => e.event === 'discarded' && e.id === id)[0];
	expect(discarded.body).toBe('raised in error');
	expect(discarded.session).toBe(sid);
	expect(discarded.undo).toBeUndefined();
	// settled, the box says so once and offers reopen alone
	await expect(head.getByTestId('outcome')).toHaveText('· discarded');
	const undo = head.getByTestId('verb-reopen');
	await expect(undo).toBeVisible();
	await expect(head.getByTestId('verb-discard')).toHaveCount(0);

	await undo.click();
	await expect.poll(() => served.log().filter((e) => e.event === 'discarded' && e.id === id).length).toBe(2);
	const reopened = served.log().filter((e) => e.event === 'discarded' && e.id === id)[1];
	expect(reopened.undo).toBe(true);
	expect(reopened.session).toBe(sid);
	await expect(head.getByTestId('verb-discard')).toBeVisible();
	await expect(head.getByTestId('outcome')).toHaveCount(0);
});

test('deleting a session from the picker tombstones it in the index, and its annotations stay in the log', async ({ page, served }) => {
	// session-delete (SessionFooter), through the confirmation that says how much is still open
	await page.goto('/node/sy-0003');
	const id = await intoASession(page, served);
	const written = served.log().filter((e) => e.session === id);
	expect(written.length).toBeGreaterThan(0);
	await openPicker(page);
	const row = page.getByTestId(`session-${id}`);
	const n = Number(/^(\d+) open$/.exec((await row.locator('.count').textContent())!.trim())![1]);
	expect(n).toBeGreaterThan(0);
	await row.hover();
	await page.getByTestId(`session-delete-${id}`).click();
	const modal = page.getByTestId('delete-session');
	// the count the modal warns of is the row's own
	await expect(modal.getByTestId('delete-open')).toContainText(`${n} annotation${n === 1 ? ' is' : 's are'} still OPEN`);
	await modal.getByTestId('delete-confirm').click();
	await expect(modal).toHaveCount(0);
	await expect.poll(() => sessionIndex(served).filter((e) => e.event === 'deleted' && e.id === id).length).toBe(1);
	expect(served.openSessions()).not.toContain(id);
	// a tombstone, not a purge: every line the session wrote is still there
	expect(served.log().filter((e) => e.session === id)).toEqual(written);
	// and the viewer lets go of it: nothing is selected, and the picker no longer lists it
	await expect(page.getByTestId('session-footer-name')).toHaveText('no session selected');
	await openPicker(page);
	await expect(page.getByTestId(`session-${id}`)).toHaveCount(0);
});

/**
 * Stage a proposed result of Kre99 into the copy: hand-written page text for the work (no PDF behind it) and a `loom refs propose` quoting it.
 *
 * The synthetic quilt carries no proposal, and a proposal's quotation is checked against the page it names, so the page text comes first. Returns the proposed node's id.
 */
function proposeKre99(served: Served, statement: string): string {
	const home = join(served.root, 'digests/storage/arxiv/math_9810166v2');
	mkdirSync(join(home, 'pages'), { recursive: true });
	writeFileSync(join(home, 'pages/0012.txt'), `Theorem 9.9. ${statement}\n`);
	writeFileSync(join(home, 'sections.json'), JSON.stringify({ sha256: '0'.repeat(64), pages: 12, chars: 80, sections: [{ n: '1', title: 'Introduction', page: 1 }] }));
	served.loom(['refs', 'propose', 'Kre99', '--local', 'thm-9.9', '--page', '12', '--level', '1', '--source-text', statement, '--statement', statement]);
	return 'Kre99-thm-9.9';
}

/** One result of a work's results file, by id. */
function resultOf(served: Served, citekey: string, id: string): Record<string, unknown> {
	const file = JSON.parse(readFileSync(join(served.root, 'digests', `${citekey}.results.json`), 'utf8')) as { results: Record<string, unknown>[] };
	return file.results.find((r) => r.id === id)!;
}

test('a proposed result is verified from its box on the digest, and the results file records it verified', async ({ page, served }) => {
	// digest-verify (ProposalBox), against a proposal loom itself stored
	const statement = 'Every cycle group of an Artin stack is generated by integral cycles.';
	const id = proposeKre99(served, statement);
	expect(resultOf(served, 'Kre99', id).state).toBe('proposed');
	await page.goto('/library/Kre99');
	await intoASession(page, served);
	await page.getByTestId('tab-digest').click();
	const box = page.locator(`[data-testid="proposal"][data-id="${id}"]`);
	await expect(box).toBeVisible({ timeout: 10000 });
	await expect(box.getByTestId('proposal-source')).toContainText('generated by integral cycles');
	await box.getByTestId('proposal-verify').click();
	await expect(box).toHaveCount(0);
	const verified = resultOf(served, 'Kre99', id);
	expect(verified.state).toBe('verified');
	expect(verified.statement).toBe(statement);
	expect((verified.origin as { act: string }[]).map((o) => o.act)).toEqual(['proposed', 'verified']);
	// nothing is left waiting, so the shadow file of proposals is gone
	expect(existsSync(join(served.root, 'digests/Kre99.proposed.tex'))).toBe(false);
});

test('a proposed result edited before it is verified records the author’s rendering and both parties', async ({ page, served }) => {
	const statement = 'Every cycle group of an Artin stack is generated by integral cycles.';
	const id = proposeKre99(served, statement);
	await page.goto('/library/Kre99');
	await intoASession(page, served);
	await page.getByTestId('tab-digest').click();
	const box = page.locator(`[data-testid="proposal"][data-id="${id}"]`);
	await expect(box).toBeVisible({ timeout: 10000 });
	await box.getByTestId('proposal-edit').click();
	const mine = 'For an Artin stack $X$, every cycle group of $X$ is generated by integral cycles.';
	await box.getByTestId('proposal-text').fill(mine);
	await box.getByTestId('proposal-send').click();
	await expect(box).toHaveCount(0);
	const verified = resultOf(served, 'Kre99', id);
	expect(verified.state).toBe('verified');
	expect(verified.statement).toBe(mine);
	// the page's words are untouched, so the result stays re-checkable against its anchor
	expect(verified.source_text).toBe(statement);
	const acts = verified.origin as { act: string; was?: string }[];
	expect(acts.map((o) => o.act)).toEqual(['proposed', 'edited', 'verified']);
	expect(acts[1].was).toBe(statement);
});

test('a proposed result is discarded from its box with the reason kept', async ({ page, served }) => {
	const id = proposeKre99(served, 'Every cycle group of an Artin stack is generated by integral cycles.');
	await page.goto('/library/Kre99');
	await intoASession(page, served);
	await page.getByTestId('tab-digest').click();
	const box = page.locator(`[data-testid="proposal"][data-id="${id}"]`);
	await expect(box).toBeVisible({ timeout: 10000 });
	await box.getByTestId('proposal-discard').click();
	await box.getByTestId('proposal-text').fill('the paper states it for schemes only');
	await box.getByTestId('proposal-send').click();
	await expect(box).toHaveCount(0);
	const gone = resultOf(served, 'Kre99', id);
	expect(gone.state).toBe('discarded');
	expect((gone.origin as { act: string }[]).map((o) => o.act)).toEqual(['proposed', 'discarded']);
	// the reason is kept in the work's proposal log, which `loom refs propose` hands back to whatever proposes it again
	const events = readFileSync(join(served.root, 'digests/Kre99.proposals.jsonl'), 'utf8').split('\n').filter((l) => l.trim()).map((l) => JSON.parse(l));
	expect(events.filter((e) => e.event === 'discarded' && e.id === id).map((e) => e.reason)).toEqual(['the paper states it for schemes only']);
});

/** The keys the copy's acceptance ledger has a row for, in order. */
function acceptedKeys(served: Served): string[] {
	return [...readFileSync(join(served.root, '.loom/state.toml'), 'utf8').matchAll(/^key = "([^"]+)"$/gm)].map((m) => m[1]);
}

/** The copy's private review decisions, by key. */
function decisions(served: Served): Record<string, { status: string }> {
	const path = join(served.root, '.loom/review-decisions.json');
	return existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : {};
}

/** Open a key of the Needs review queue and mark it OK, as the guided review does. */
async function markOk(page: import('@playwright/test').Page, key: string): Promise<void> {
	await page.goto('/review?show=needs-review');
	await page.getByRole('button', { name: key, exact: true }).click();
	const guided = page.getByTestId('guided-review');
	await expect(guided.locator('h2')).toContainText(key);
	await guided.getByRole('button', { name: 'OK', exact: true }).click();
}

test('finishing review over an OK whose dependency is still stale is refused, and nothing is accepted', async ({ page, served }) => {
	// review-finish: sy-0002 rests on sy-0001, which is stale and has no decision, so accepting sy-0002 first would record it against an unreviewed context
	const ledger = acceptedKeys(served);
	await markOk(page, 'sy-0002');
	await expect.poll(() => decisions(served)['sy-0002']?.status).toBe('ok');
	const finish = page.getByRole('button', { name: /^Finish review · record 1 acceptances$/ });
	await finish.click();
	await expect(page.getByRole('alert')).toHaveText('review sy-0001 before finishing sy-0002');
	expect(acceptedKeys(served)).toEqual(ledger);
	// the decision waits rather than being dropped
	expect(decisions(served)['sy-0002']?.status).toBe('ok');
});

test('finishing review records an acceptance for each pending OK, and clears the decision', async ({ page, served }) => {
	// Finish accepts only when the master compiles; a PDF newer than every source is loom's sign that it already did, so no TeX run happens in this suite (the compile itself is loom's to test).
	mkdirSync(join(served.root, 'build/main'), { recursive: true });
	writeFileSync(join(served.root, 'build/main/main.pdf'), '%PDF-1.4\n');
	const ledger = acceptedKeys(served);
	await markOk(page, 'sy-0001');
	await expect.poll(() => decisions(served)['sy-0001']?.status).toBe('ok');
	await page.getByRole('button', { name: /^Finish review · record 1 acceptances$/ }).click();
	await expect.poll(() => acceptedKeys(served)).toEqual([...ledger, 'sy-0001']);
	const row = readFileSync(join(served.root, '.loom/state.toml'), 'utf8').split('[[accept]]').at(-1)!;
	expect(row).toContain('key = "sy-0001"');
	expect(row).toContain('master = "drafting/main.tex"');
	expect(row).not.toContain('2026-09-14T09:00:00Z'); // a new row, dated now, not the fixture's
	expect(decisions(served)['sy-0001']).toBeUndefined();
	await expect(page.getByRole('alert')).toHaveCount(0);
	// and once the publisher has rebuilt, the key has left the queue
	await expect(page.getByRole('button', { name: 'sy-0001', exact: true })).toHaveCount(0, { timeout: 10000 });
});
