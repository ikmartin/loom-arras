// Measuring one action in the page: Chrome's own task, script, style and layout time around it, every long task, every frame interval, and the time until the page has painted and gone quiet. Results are printed and appended to test-results/perf-live.jsonl.

import type { CDPSession, Page } from '@playwright/test';
import { appendFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { ARRAS } from '../served';

declare global {
	interface Window {
		__perf?: { long: { start: number; dur: number }[]; frames: number[]; recording: boolean };
	}
}

export interface Measured {
	name: string;
	/** Input to settled, ms. */
	wall: number;
	task: number;
	script: number;
	style: number;
	layout: number;
	styleCount: number;
	layoutCount: number;
	longest: number;
	longCount: number;
	frames: number;
	frameP95: number;
	janky: number;
	nodes: number;
	note: string;
}

const OUT = join(ARRAS, 'test-results', 'perf-live.jsonl');
/** Whether a budget fails the test; `PERF_ENFORCE=0` only reports. */
export const enforce = process.env.PERF_ENFORCE !== '0';

/** Install the long-task and frame recorder before the page's own scripts, and open the page's CDP session. */
export async function instrument(page: Page): Promise<CDPSession> {
	await page.addInitScript(() => {
		const w = window;
		w.__perf = { long: [], frames: [], recording: false };
		try {
			new PerformanceObserver((l) => {
				for (const e of l.getEntries()) w.__perf!.long.push({ start: e.startTime, dur: e.duration });
			}).observe({ type: 'longtask', buffered: true });
		} catch {
			/* no long-task timing in this browser */
		}
		let last = 0;
		const tick = (t: number) => {
			if (w.__perf!.recording && last) w.__perf!.frames.push(t - last);
			last = t;
			requestAnimationFrame(tick);
		};
		requestAnimationFrame(tick);
	});
	const cdp = await page.context().newCDPSession(page);
	await cdp.send('Performance.enable');
	// a forced collection is only carried out with the heap profiler enabled; without it `liveNodes` counted garbage
	await cdp.send('HeapProfiler.enable');
	return cdp;
}

async function metrics(cdp: CDPSession): Promise<Record<string, number>> {
	const { metrics: list } = await cdp.send('Performance.getMetrics');
	return Object.fromEntries(list.map((x) => [x.name, x.value]));
}

/** Wait until the page has painted twice and no long task has run for `quiet` ms. */
export async function settle(page: Page, quiet = 400, cap = 30000): Promise<void> {
	const t0 = Date.now();
	while (Date.now() - t0 < cap) {
		const idle = await page.evaluate(
			(q) =>
				new Promise<boolean>((done) =>
					requestAnimationFrame(() =>
						requestAnimationFrame(() => {
							const l = window.__perf?.long ?? [];
							const end = l.length ? Math.max(...l.map((e) => e.start + e.dur)) : 0;
							done(performance.now() - end > q);
						})
					)
				),
			quiet
		);
		if (idle) return;
		await page.waitForTimeout(100);
	}
}

/** Every formula in the open fragments typeset. */
export async function typesetAll(page: Page): Promise<void> {
	// a function rather than a selector wait: `waitForSelector` returns a handle to the element, which keeps the whole document it is in alive
	await page.waitForFunction(
		() => !!document.querySelector('[data-pane="0"] .fragment mjx-container') && document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0,
		null,
		{ polling: 200, timeout: 60000 }
	);
}

/** DOM nodes alive after two forced collections: what the page holds, garbage excluded. */
export async function liveNodes(cdp: CDPSession): Promise<number> {
	await cdp.send('HeapProfiler.collectGarbage');
	await cdp.send('HeapProfiler.collectGarbage');
	return (await metrics(cdp)).Nodes ?? 0;
}

/** Measure `run`; the clock stops at the later of `run` returning and the last long task it caused. */
export async function measure(page: Page, cdp: CDPSession, name: string, run: () => Promise<string | void>, quiet = 400): Promise<Measured> {
	await settle(page, 300);
	await page.evaluate(() => {
		if (!window.__perf) return;
		window.__perf.long = [];
		window.__perf.frames = [];
		window.__perf.recording = true;
	});
	const before = await metrics(cdp);
	const p0 = await page.evaluate(() => performance.now());
	const t0 = Date.now();
	const note = (await run()) ?? '';
	const acted = Date.now() - t0;
	await settle(page, quiet);
	const after = await metrics(cdp);
	const perf = await page.evaluate(() => {
		const p = window.__perf ?? { long: [], frames: [], recording: false };
		p.recording = false;
		return { long: p.long, frames: p.frames };
	});
	const lastLong = perf.long.length ? Math.max(...perf.long.map((e) => e.start + e.dur)) : 0;
	const f = [...perf.frames].sort((a, b) => a - b);
	const d = (k: string) => (after[k] ?? 0) - (before[k] ?? 0);
	const m: Measured = {
		name,
		wall: Math.round(Math.max(acted, lastLong ? lastLong - p0 : 0)),
		task: Math.round(d('TaskDuration') * 1000),
		script: Math.round(d('ScriptDuration') * 1000),
		style: Math.round(d('RecalcStyleDuration') * 1000),
		layout: Math.round(d('LayoutDuration') * 1000),
		styleCount: d('RecalcStyleCount'),
		layoutCount: d('LayoutCount'),
		longest: Math.round(Math.max(0, ...perf.long.map((e) => e.dur))),
		longCount: perf.long.length,
		frames: f.length,
		frameP95: Math.round(f.length ? f[Math.min(f.length - 1, Math.floor(0.95 * f.length))] : 0),
		janky: f.filter((x) => x > 50).length,
		nodes: after.Nodes ?? 0,
		note
	};
	report(m);
	return m;
}

/** Print one result and append it to the suite's log. */
export function report(m: Measured | (Partial<Measured> & { name: string })): void {
	mkdirSync(join(ARRAS, 'test-results'), { recursive: true });
	appendFileSync(OUT, JSON.stringify({ at: new Date().toISOString(), ...m }) + '\n');
	console.log(`  ${m.name}: ${Object.entries(m).filter(([k]) => k !== 'name').map(([k, v]) => `${k} ${v}`).join(', ')}`);
}

/** Drag along y through `stops`, `steps` moves between each two, in one press: a move every 8 ms, as a 120 Hz pointer sends them, never waiting on the page.
 *
 * Waiting a frame after each move, as this once did, put idle frames between the moves, and a frame count over them hid what every frame costs when the pointer moves in each one. */
export async function drag(page: Page, y: number, stops: number[], steps = 40): Promise<void> {
	await page.mouse.move(stops[0], y);
	await page.mouse.down();
	for (let k = 1; k < stops.length; k++) {
		for (let i = 1; i <= steps; i++) {
			const sent = Date.now();
			await page.mouse.move(stops[k - 1] + ((stops[k] - stops[k - 1]) * i) / steps, y);
			const rest = 8 - (Date.now() - sent);
			if (rest > 0) await page.waitForTimeout(rest);
		}
	}
	await page.mouse.up();
}

interface TraceEvent {
	name: string;
	ph: string;
	ts: number;
	args?: { data?: { type?: string }; frame_reporter?: { state?: string; has_main_animation?: boolean } };
}

export interface Presented {
	/** Frames with the page's own changes that reached the screen while the pointer moved. */
	shown: number;
	dropped: number;
	/** Between two shown frames, ms. */
	median: number;
	p95: number;
}

/** The frames that reached the screen while `run` moved the pointer, from Chrome's trace: the compositor's record of each frame carrying the page's changes, shown or dropped, between the first and the last pointermove.
 *
 * Not from requestAnimationFrame: its timestamp is when a frame was begun, not when the main thread reached it, so frames held up behind 50 ms of layout still read as 17 ms apart. */
export async function presented(page: Page, run: () => Promise<void>): Promise<Presented> {
	const browser = page.context().browser()!;
	await browser.startTracing(page, { categories: ['devtools.timeline', 'disabled-by-default-devtools.timeline.frame'] });
	await run();
	const { traceEvents } = JSON.parse((await browser.stopTracing()).toString()) as { traceEvents: TraceEvent[] };
	const moves = traceEvents.filter((e) => e.name === 'EventDispatch' && e.args?.data?.type === 'pointermove').map((e) => e.ts);
	const from = Math.min(...moves);
	const to = Math.max(...moves);
	const frames = traceEvents.filter((e) => e.name === 'PipelineReporter' && e.ph === 'b' && e.ts >= from && e.ts <= to && e.args?.frame_reporter?.has_main_animation);
	const shown = frames.filter((e) => e.args!.frame_reporter!.state?.startsWith('STATE_PRESENTED')).map((e) => e.ts).sort((a, b) => a - b);
	const gaps = shown.slice(1).map((t, i) => (t - shown[i]) / 1000).sort((a, b) => a - b);
	const at = (q: number) => Math.round(gaps.length ? gaps[Math.min(gaps.length - 1, Math.floor(q * gaps.length))] : 0);
	return { shown: shown.length, dropped: frames.filter((e) => e.args!.frame_reporter!.state === 'STATE_DROPPED').length, median: at(0.5), p95: at(0.95) };
}
