// Round two: the candidates that survived round one, measured without a fetch inside the timed region.
import { test } from '@playwright/test';

test('what actually helps', async ({ page }) => {
	await page.goto('/');
	await page.waitForSelector('main h1');
	const doc = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		(window as any).__m = m;
		const master = m.masters.find((x: any) => x.default) ?? m.masters[0];
		return '/master/' + master.path.replace(/^.*\//, '').replace(/\.tex$/, '');
	});
	await page.goto(doc);
	await page.waitForSelector('.fragment');
	await page.waitForTimeout(2500);

	const out = await page.evaluate(async () => {
		const m = await (await fetch(new URL('/build/manifest.json', location.href))).json();
		const frame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
		const flip = () => {
			const el = document.documentElement;
			el.setAttribute('data-size', el.getAttribute('data-size') === 'l' ? 'm' : 'l');
		};
		const results: Record<string, number> = {};
		const run = async (name: string, fn: () => Promise<void> | void) => {
			const t = performance.now();
			await fn();
			results[name] = Math.round(performance.now() - t);
		};

		// A: the baseline flip, waiting for the paint that follows it
		await run('A baseline flip (to paint)', async () => {
			flip();
			await frame();
		});

		// B: how long the click handler itself blocks, which is what a button's own repaint waits on
		await run('B the synchronous part of a flip', () => {
			flip();
		});

		// C: per-key filtering over every annotation, as commentsOn does today
		const keys = Object.keys(m.keys);
		const annotations = Object.values(m.annotations) as any[];
		await run('C filter per key (today)', () => {
			let n = 0;
			for (const k of keys) n += annotations.filter((a) => a.target.key === k).length;
			if (n < 0) throw new Error();
		});

		// D: the same answer from one index
		await run('D index once, then look up', () => {
			const by = new Map<string, any[]>();
			for (const a of annotations) {
				const l = by.get(a.target.key);
				if (l) l.push(a);
				else by.set(a.target.key, [a]);
			}
			let n = 0;
			for (const k of keys) n += (by.get(k) ?? []).length;
			if (n < 0) throw new Error();
		});

		// E: containment on the blocks, then a flip
		const s = document.createElement('style');
		s.textContent = '.fragment .env { contain: layout style; }';
		document.head.appendChild(s);
		await frame();
		await run('E flip with contain:layout style', async () => {
			flip();
			await frame();
		});
		s.remove();

		// F: containment on the math itself, which is where the element count actually is
		const s2 = document.createElement('style');
		s2.textContent = 'mjx-container { content-visibility: auto; contain-intrinsic-size: auto 1.2em; }';
		document.head.appendChild(s2);
		await frame();
		await run('F flip, math content-visibility', async () => {
			flip();
			await frame();
		});
		s2.remove();

		// G: the same, applied to whole sections so off-screen prose is skipped too
		const s3 = document.createElement('style');
		s3.textContent = '.fragment > section, .fragment .included { content-visibility: auto; contain-intrinsic-size: auto 600px; }';
		document.head.appendChild(s3);
		await frame();
		await run('G flip, section content-visibility', async () => {
			flip();
			await frame();
		});
		s3.remove();

		// H: how much of it is the math at all -- the same flip with every formula hidden
		await run('H flip, math display:none', async () => {
			const s4 = document.createElement('style');
			s4.textContent = 'mjx-container { display: none; }';
			document.head.appendChild(s4);
			await frame();
			flip();
			await frame();
			s4.remove();
		});

		return { results, keys: keys.length, annotations: annotations.length, elements: document.querySelectorAll('*').length, math: document.querySelectorAll('mjx-container *').length };
	});

	// eslint-disable-next-line no-console
	console.log('\n  corpus: ' + out.keys + ' keys, ' + out.annotations + ' annotations, ' + out.elements + ' elements of which ' + out.math + ' are inside math');
	for (const [k, v] of Object.entries(out.results)) {
		// eslint-disable-next-line no-console
		console.log(`  ${k.padEnd(40)} ${v} ms`);
	}
});
