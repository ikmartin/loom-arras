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
	await page.waitForSelector('[data-pane="0"] .fragment mjx-container', { timeout: 60000 });
	await page.waitForFunction(() => document.querySelectorAll('.fragment .math:not(:has(mjx-container))').length === 0, null, { polling: 200, timeout: 60000 });
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

/** Drag from (x0, y) to (x1, y) in `steps` moves, one per animation frame, as a hand would. */
export async function drag(page: Page, x0: number, y: number, x1: number, steps = 40): Promise<void> {
	await page.mouse.move(x0, y);
	await page.mouse.down();
	for (let i = 1; i <= steps; i++) {
		await page.mouse.move(x0 + ((x1 - x0) * i) / steps, y);
		await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => r())));
	}
	await page.mouse.up();
}
