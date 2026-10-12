// The viewer's speed on a large paper under a running publisher. Each test gets its own served copy of the prepared quilt (setup.ts) and its own browser context.
//
// The budgets are floors, set at about twice what was reached (plan 0.19, and DR-341-ikmartin for the divider), so a return of what was removed fails and the noise of a busy machine does not; the plan's own targets, and which it met, are in its Delivery.

import type { Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { expect, test } from '../served';
import { drag, enforce, instrument, liveNodes, measure, presented, report, settle, typesetAll, type Presented } from './measure';
import { phrases, reading } from './setup';

interface Corpus {
	doc: string;
	node: string | undefined;
	work: string | undefined;
	nodes: [string, { file?: string }][];
}

function corpus(root: string): Corpus {
	const { master, nodes } = reading(root);
	const m = JSON.parse(readFileSync(join(root, 'build', 'manifest.json'), 'utf8')) as { references: Record<string, { artifacts?: { pdf?: boolean } }> };
	return {
		doc: '/master/' + basename(master.path, '.tex'),
		node: nodes.find(([, n]) => n.kind === 'environment')?.[0],
		work: Object.entries(m.references).find(([, r]) => r.artifacts?.pdf)?.[0],
		nodes
	};
}

const nodeUrl = (key: string) => '/node/' + key.split('/').map(encodeURIComponent).join('/');
const beside = (path: string) => '?beside=' + encodeURIComponent(path);

/** A budget: fails the test unless the suite only reports (`PERF_ENFORCE=0`). */
function budget(ok: boolean, what: string): void {
	if (enforce) expect(ok, what).toBe(true);
}

async function openDocument(page: Page, path: string): Promise<void> {
	await page.goto(path);
	await typesetAll(page);
	await settle(page, 600);
}

async function dragDivider(page: Page, name: string, cdp: Awaited<ReturnType<typeof instrument>>): Promise<void> {
	const handle = (await page.getByTestId('divider').boundingBox())!;
	const frame = (await page.getByTestId('workspace').boundingBox())!;
	const y = handle.y + handle.height / 2;
	let frames: Presented | undefined;
	const m = await measure(page, cdp, name, async () => {
		frames = await presented(page, () => drag(page, y, [handle.x + handle.width / 2, frame.x + frame.width * 0.3, frame.x + frame.width * 0.65], 60));
		return `${frames.shown} frames shown, ${frames.dropped} dropped`;
	});
	const perMove = Math.round(m.task / 120);
	report({ name: `${name}, per move`, task: perMove });
	report({ name: `${name}, frames shown`, frames: frames!.shown, frameP95: frames!.p95, note: `median ${frames!.median} ms, ${frames!.dropped} dropped` });
	budget(perMove <= 16, `${name}: ${perMove} ms of work per move, budget 16`);
	budget(frames!.p95 <= 34, `${name}: shown frames p95 ${frames!.p95} ms apart, budget 34`);
}

test('cold load of the main document', async ({ page, served }) => {
	const { doc } = corpus(served.root);
	const cdp = await instrument(page);
	await measure(page, cdp, 'cold load', async () => {
		await page.goto(doc);
		await typesetAll(page);
	}, 600);
});

test('the divider, beside a node', async ({ page, served }) => {
	const { doc, node } = corpus(served.root);
	test.skip(!node, 'the main document reaches no node');
	const cdp = await instrument(page);
	await openDocument(page, doc + beside(nodeUrl(node!)));
	await dragDivider(page, 'divider beside a node', cdp);
});

test('the divider, beside a PDF', async ({ page, served }) => {
	const { doc, work } = corpus(served.root);
	test.skip(!work, 'no work has a filed PDF');
	const cdp = await instrument(page);
	await openDocument(page, doc + beside(`/library/${work}?page=1`));
	await page.locator('[data-testid="pdf-page-1"] canvas').waitFor();
	await settle(page, 600);
	await dragDivider(page, 'divider beside a PDF', cdp);
});

test('five returns from the graph keep memory flat and cost little', async ({ page, served }) => {
	const { doc } = corpus(served.root);
	const cdp = await instrument(page);
	await openDocument(page, doc);
	let first = 0;
	let worst = 0;
	for (let i = 1; i <= 5; i++) {
		await page.getByTestId('view-graph').click();
		await page.locator('svg g.node').first().waitFor();
		await settle(page, 300);
		const m = await measure(page, cdp, `back from the graph, ${i}`, async () => {
			await page.getByTestId('view-read').click();
			await typesetAll(page);
		});
		if (i > 1) worst = Math.max(worst, m.wall);
		if (i === 1) first = await liveNodes(cdp);
	}
	const last = await liveNodes(cdp);
	report({ name: 'live DOM nodes after the first and the fifth return', note: `${first} -> ${last}` });
	budget(last <= first * 1.05, `live DOM nodes grew from ${first} to ${last}`);
	budget(worst <= 600, `a return from the graph took ${worst} ms, budget 600`);
});

test('a tab switch back to the document', async ({ page, served }) => {
	const { doc } = corpus(served.root);
	const cdp = await instrument(page);
	await openDocument(page, doc);
	await page.getByTestId('library-list').getByRole('link').first().click();
	await settle(page, 600);
	const m = await measure(page, cdp, 'tab back to the document', async () => {
		await page.getByTestId('pane-0').getByTestId('item-tab').first().getByRole('tab').click();
		await typesetAll(page);
	});
	budget(m.wall <= 600, `the tab switch took ${m.wall} ms, budget 600`);
});

test('ten annotations arrive while the author reads', async ({ page, served }) => {
	const { doc, nodes } = corpus(served.root);
	const cdp = await instrument(page);
	await openDocument(page, doc);
	const body = page.getByTestId('pane-0').locator('> .body');
	await body.evaluate((el) => el.scrollTo(0, el.scrollHeight * 0.6));
	await settle(page, 600);
	// counted from the first arrival on: the first patch keeps the published markup parsed for the next, once
	let start = 0;
	// what the reader sees at the pane's top, and where: the scroll offset itself moves whenever the browser keeps the text still as sizes above it change
	const seen = () =>
		body.evaluate((el) => {
			const r = el.getBoundingClientRect();
			// the first block of text, not a section around it, whose top may be thousands of pixels up while its words above the reader change size
			const block = [...el.querySelectorAll<HTMLElement>('[data-src]')].filter((e) => !e.querySelector('[data-src]')).find((e) => e.getBoundingClientRect().bottom > r.top + 48);
			return block ? { src: block.dataset.src ?? '', top: block.getBoundingClientRect().top - r.top } : null;
		});
	const place = await seen();
	let filed = 0;
	for (const [key, node] of nodes) {
		if (filed >= 10) break;
		const quote = phrases(readFileSync(join(served.root, node.file!), 'utf8'))[1];
		if (!quote) continue;
		await page.evaluate(() => window.__perf && (window.__perf.long = []));
		let id = '';
		try {
			id = served.loom(['annotate', key, `Arrived ${filed}.`, '--quote', quote, '--as', 'Perf Agent']).split(/\s+/)[0];
		} catch {
			continue;
		}
		const t0 = Date.now();
		await page.locator(`[data-pane="0"] .fragment [data-annotation~="${id}"]`).first().waitFor({ state: 'attached' });
		const drawn = Date.now() - t0;
		await typesetAll(page);
		await settle(page, 500);
		const longest = await page.evaluate(() => Math.round(Math.max(0, ...(window.__perf?.long ?? []).map((e) => e.dur))));
		filed++;
		if (filed === 1) start = await liveNodes(cdp);
		report({ name: `annotation ${filed} drawn`, wall: drawn, longest });
		budget(drawn <= 1000, `annotation ${filed} took ${drawn} ms to be drawn, budget 1000`);
		budget(longest <= 100, `annotation ${filed} caused a ${longest} ms task, budget 100`);
	}
	expect(filed, 'annotations filed').toBeGreaterThanOrEqual(5);
	const end = await liveNodes(cdp);
	const moved = place
		? await body.evaluate((el, p) => {
				const block = el.querySelector<HTMLElement>(`[data-src="${CSS.escape(p.src)}"]`);
				return block ? Math.abs(block.getBoundingClientRect().top - el.getBoundingClientRect().top - p.top) : Infinity;
			}, place)
		: 0;
	report({ name: `live DOM nodes from the first to the last of ${filed} annotations`, note: `${start} -> ${end}; the text at the pane's top moved ${Math.round(moved)} px` });
	budget(end <= start * 1.05, `live DOM nodes grew from ${start} to ${end}`);
	budget(moved <= 4, `the text at the pane's top moved ${Math.round(moved)} px, budget 4`);
});

test('the graph opens without a long task', async ({ page, served }) => {
	const { doc } = corpus(served.root);
	const cdp = await instrument(page);
	await openDocument(page, doc);
	const m = await measure(page, cdp, 'open the graph', async () => {
		await page.getByTestId('view-graph').click();
		await page.locator('svg g.node').first().waitFor();
	}, 600);
	budget(m.longest <= 100, `opening the graph ran a ${m.longest} ms task, budget 100`);
});

test('a PDF scrolls without a long task', async ({ page, served }) => {
	const { work } = corpus(served.root);
	test.skip(!work, 'no work has a filed PDF');
	const cdp = await instrument(page);
	await page.goto(`/library/${work}?page=1`);
	await page.locator('[data-testid="pdf-page-1"] canvas').waitFor();
	await settle(page, 600);
	const column = (await page.getByTestId('pdf-doc').locator('.column').boundingBox())!;
	await page.mouse.move(column.x + column.width / 2, column.y + column.height / 2);
	const m = await measure(page, cdp, 'scroll the PDF, 40 wheel steps', async () => {
		for (let i = 0; i < 40; i++) {
			await page.mouse.wheel(0, 700);
			await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => r())));
		}
	}, 600);
	// the layouts it runs are PDF.js's own: its text layer measures every span on a canvas kept in the document, which makes the browser restyle as each one is put in
	budget(m.longest <= 50, `scrolling the PDF ran a ${m.longest} ms task, budget 50`);
	budget(m.frameP95 <= 67, `scrolling the PDF: frame p95 ${m.frameP95} ms, budget 67`);
});

test('settings that restyle the document', async ({ page, served }) => {
	const { doc } = corpus(served.root);
	const cdp = await instrument(page);
	await openDocument(page, doc);
	await page.getByTestId('settings-toggle').click();
	await page.getByTestId('settings-panel').waitFor();
	await measure(page, cdp, 'text size M to L', async () => void (await page.getByTestId('size-l').click()));
	await measure(page, cdp, 'format p1 to b1', async () => void (await page.getByTestId('format-b1').click()));
});

test('ten seconds idle', async ({ page, served }) => {
	const { doc } = corpus(served.root);
	const cdp = await instrument(page);
	await openDocument(page, doc);
	await measure(page, cdp, 'idle 10 s', async () => void (await page.waitForTimeout(10000)));
});
