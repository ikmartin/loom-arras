<script lang="ts" module>
	/** What a tool drew, in points from the page's top left, and where that is on screen for a form to stand beside. */
	export type Drawn = { kind: MarkKind; rects?: number[][]; strokes?: number[][]; client: { left: number; top: number; width: number; height: number } };
	/** Where a moved mark now stands. */
	export type Moved = { id: string; rects: number[][]; strokes?: number[][] };
</script>

<script lang="ts">
	// One page's marks, and the drawing of new ones (plan 0.28).
	//
	// **A dumb renderer**, as `PdfPage` is: it is given the marks and the tool and it reports what the reader drew, picked or moved, writing nothing and knowing nothing of notes.
	//
	// **Highlights stand on a layer of their own**, multiplied over the page so the words under them stay black. It cannot be inside the layer of the rest, which is a stacking context of its own and would multiply against nothing.
	//
	// **A mark takes no pointer**, so a press on a highlight begins a selection like a press on any other words, and `PdfPage` asks `markAt` where a click landed. Each mark still has its button, which takes the keyboard and says what the mark is; a pin's and words on the page also take the pointer, since nothing lies under them to select. The tools that draw take the whole page's pointer while they are up.
	import Icon from '$lib/components/Icon.svelte';
	import { asPercent } from './document';
	import { prefs } from '$lib/prefs.svelte';
	import { bound, DRAWING, kindOf, movable, ON_WORDS, paintOf, refit, simplify, type MarkKind, type PageMark } from './marks';
	import { arrowHead, TEXT_SIZE } from './portable';

	let {
		marks = [],
		box,
		scale,
		tool = 'select',
		selected = '',
		embedded = [],
		ondraw,
		onpick,
		onmove
	}: {
		marks?: PageMark[];
		/** The page's size in points. */
		box: { width: number; height: number };
		scale: number;
		tool?: string;
		selected?: string;
		/** The PDF's own comments on this page, each with a button that names it for the keyboard. */
		embedded?: { id: string; subtype: string; rects: number[][]; body: string }[];
		ondraw?: (e: Drawn) => void;
		onpick?: (e: { id: string }) => void;
		onmove?: (e: Moved) => void;
	} = $props();

	let host = $state<HTMLDivElement | null>(null);
	const drawing = $derived(DRAWING.includes(tool));
	/** The stroke or the corner-to-corner drag under the pointer. */
	let line = $state<number[] | null>(null);
	type Grip = 'move' | 'nw' | 'ne' | 'sw' | 'se';
	let grip = $state<{ id: string; how: Grip; x: number; y: number; from: number[] } | null>(null);
	let held = $state<number[] | null>(null);

	const shown = $derived(marks.map((m) => (grip && held && m.id === grip.id ? { ...m, ...refit(m, held) } : m)));
	const chosen = $derived(shown.find((m) => m.id === selected && movable(m)));
	const bands = $derived(shown.filter((m) => m.kind === 'highlight'));
	const drawn = $derived(shown.filter((m) => m.kind !== 'highlight'));

	function at(e: PointerEvent): [number, number] {
		const r = host!.getBoundingClientRect();
		return [((e.clientX - r.left) * box.width) / (r.width || 1), ((e.clientY - r.top) * box.height) / (r.height || 1)];
	}

	function begin(e: PointerEvent): void {
		if (!drawing || e.button !== 0) return;
		e.preventDefault();
		host!.setPointerCapture(e.pointerId);
		line = at(e);
	}

	function extend(e: PointerEvent): void {
		if (!line) return;
		const [x, y] = at(e);
		if (tool === 'ink') line = [...line, x, y];
		else line = [line[0], line[1], x, y];
	}

	function clientOf(x0: number, y0: number, x1: number, y1: number): Drawn['client'] {
		const r = host!.getBoundingClientRect();
		const k = r.width / (box.width || 1);
		return { left: r.left + x0 * k, top: r.top + y0 * k, width: (x1 - x0) * k, height: (y1 - y0) * k };
	}

	function finish(e: PointerEvent): void {
		const drawn = line;
		line = null;
		if (!drawn) return;
		host!.releasePointerCapture(e.pointerId);
		const kind = kindOf(tool);
		if (!kind) return;
		const [x0, y0] = drawn;
		const [x1, y1] = drawn.length >= 4 ? [drawn[drawn.length - 2], drawn[drawn.length - 1]] : [x0, y0];
		if (tool === 'pin') {
			const r = [x0 - 8, y0 - 8, x0 + 8, y0 + 8];
			ondraw?.({ kind, rects: [r], client: clientOf(r[0], r[1], r[2], r[3]) });
		} else if (tool === 'text') {
			const r = [x0, y0, x0 + 220, y0 + 18];
			ondraw?.({ kind, rects: [r], client: clientOf(r[0], r[1], r[2], r[3]) });
		} else if (tool === 'ink') {
			if (drawn.length < 4) return;
			const s = simplify(drawn);
			const b = bound([[x0, y0, x0, y0], ...pairs(drawn).map(([x, y]) => [x, y, x, y])]);
			ondraw?.({ kind, strokes: [s], client: clientOf(b[0], b[1], b[2], b[3]) });
		} else {
			// a press with no drag draws nothing
			if (Math.abs(x1 - x0) < 3 && Math.abs(y1 - y0) < 3) return;
			const [l, t, r, b] = [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)];
			const place = tool === 'arrow' ? { strokes: [[x0, y0, x1, y1].map((v) => Math.round(v * 10) / 10)] } : { rects: [[l, t, r, b].map((v) => Math.round(v * 10) / 10)] };
			ondraw?.({ kind, ...place, client: clientOf(l, t, r, b) });
		}
	}

	function pairs(flat: readonly number[]): [number, number][] {
		const out: [number, number][] = [];
		for (let i = 0; i + 1 < flat.length; i += 2) out.push([flat[i], flat[i + 1]]);
		return out;
	}

	const pointsOf = (s: readonly number[]) => pairs(s).map(([x, y]) => `${x},${y}`).join(' ');

	function takeGrip(e: PointerEvent, how: Grip): void {
		if (!chosen || e.button !== 0) return;
		e.preventDefault();
		e.stopPropagation();
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		const [x, y] = at(e);
		grip = { id: chosen.id, how, x, y, from: bound(chosen.rects) };
		held = grip.from;
	}

	function pull(e: PointerEvent): void {
		if (!grip) return;
		const [x, y] = at(e);
		const [dx, dy] = [x - grip.x, y - grip.y];
		const [x0, y0, x1, y1] = grip.from;
		if (grip.how === 'move') held = [x0 + dx, y0 + dy, x1 + dx, y1 + dy];
		else {
			const next = [x0 + (grip.how.includes('w') ? dx : 0), y0 + (grip.how.includes('n') ? dy : 0), x1 + (grip.how.includes('e') ? dx : 0), y1 + (grip.how.includes('s') ? dy : 0)];
			held = [Math.min(next[0], next[2] - 6), Math.min(next[1], next[3] - 6), Math.max(next[2], next[0] + 6), Math.max(next[3], next[1] + 6)];
		}
	}

	function letGo(): void {
		if (!grip) return;
		const { id, from } = grip;
		const to = held;
		const m = marks.find((n) => n.id === id);
		grip = held = null;
		if (m && to && to.some((v, i) => Math.abs(v - from[i]) >= 0.5)) onmove?.({ id, ...refit(m, to) });
	}

	const label = (m: PageMark) => (m.plain ? 'a note' : `${m.color ? `${m.color} ` : ''}${m.kind}`) + (m.quote ? `: ${m.quote}` : m.body ? `: ${m.body}` : '');
</script>

<svg class="bands" viewBox="0 0 {box.width} {box.height}" preserveAspectRatio="none" aria-hidden="true">
	{#each bands as m (m.id)}
		<g class="m" class:on={m.id === selected} style={paintOf(m.color)} data-testid="mark-band-{m.id}">
			{#each m.rects as r, i (i)}
				<rect class="band" x={r[0]} y={r[1]} width={r[2] - r[0]} height={r[3] - r[1]} />
			{/each}
		</g>
	{/each}
</svg>
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="page-marks" class:drawing class:idle={tool !== 'select'} bind:this={host} data-testid="page-marks" onpointerdown={begin} onpointermove={extend} onpointerup={finish}>
	<svg viewBox="0 0 {box.width} {box.height}" preserveAspectRatio="none" aria-hidden="true">
		{#each drawn as m (m.id)}
			<g class="m k-{m.kind}" class:plain={m.plain} class:on={m.id === selected} style={paintOf(m.color)}>
				{#if ON_WORDS.includes(m.kind)}
					{#each m.rects as r, i (i)}
						{@const y = m.kind === 'strike' ? (r[1] + r[3]) / 2 : r[3]}
						<line class="rule" x1={r[0]} x2={r[2]} y1={y} y2={y} />
					{/each}
				{:else if m.kind === 'box'}
					{@const r = m.rects[0]}
					<rect class="shape" x={r[0]} y={r[1]} width={r[2] - r[0]} height={r[3] - r[1]} />
				{:else if m.kind === 'oval'}
					{@const r = m.rects[0]}
					<ellipse class="shape" cx={(r[0] + r[2]) / 2} cy={(r[1] + r[3]) / 2} rx={(r[2] - r[0]) / 2} ry={(r[3] - r[1]) / 2} />
				{:else if m.strokes}
					{#each m.strokes as s, i (i)}
						<polyline class="shape" points={pointsOf(s)} />
						{#if m.kind === 'arrow'}
							{#each arrowHead(s) as wing, k (k)}<polyline class="shape" points={pointsOf(wing)} />{/each}
						{/if}
					{/each}
				{/if}
			</g>
		{/each}
		{#if line && line.length >= 4}
			<g class="m on" style={paintOf(prefs.markColor)}>
				{#if tool === 'ink'}
					<polyline class="shape" points={pointsOf(line)} />
				{:else if tool === 'rect'}
					<rect class="shape" x={Math.min(line[0], line[2])} y={Math.min(line[1], line[3])} width={Math.abs(line[2] - line[0])} height={Math.abs(line[3] - line[1])} />
				{:else if tool === 'oval'}
					<ellipse class="shape" cx={(line[0] + line[2]) / 2} cy={(line[1] + line[3]) / 2} rx={Math.abs(line[2] - line[0]) / 2} ry={Math.abs(line[3] - line[1]) / 2} />
				{:else if tool === 'arrow'}
					<polyline class="shape" points={pointsOf(line)} />
					{#each arrowHead(line) as wing, k (k)}<polyline class="shape" points={pointsOf(wing)} />{/each}
				{/if}
			</g>
		{/if}
	</svg>
	{#each shown as m (m.id)}
		{@const place = asPercent(bound(m.rects), box)}
		<button
			type="button"
			class="hit"
			class:pin={m.kind === 'pin'}
			class:words={m.kind === 'text'}
			class:on={m.id === selected}
			data-mark={m.id}
			data-kind={m.kind}
			data-testid="page-mark-{m.id}"
			aria-label={label(m)}
			style="left: {place.left}; top: {place.top}; width: {place.width}; height: {place.height};{m.kind === 'text' ? ` font-size: ${TEXT_SIZE * scale}px;` : ''} {paintOf(m.color)}"
			onclick={(e) => {
				e.stopPropagation();
				onpick?.({ id: m.id });
			}}
		>
			{#if m.kind === 'pin'}<Icon name="pin" size={Math.round(16 * scale)} />{:else if m.kind === 'text'}{m.body}{/if}
		</button>
	{/each}
	{#each embedded as a (a.id)}
		{@const place = asPercent(a.rects[0], box)}
		<span class="embedded" data-testid="pdf-annotation-{a.id}" aria-label="{a.subtype} in the PDF: {a.body}" style="left: {place.left}; top: {place.top}; width: {place.width}; height: {place.height};"></span>
	{/each}
	{#if chosen}
		{@const place = asPercent(bound(chosen.rects), box)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="grab" data-testid="mark-grab" style="left: {place.left}; top: {place.top}; width: {place.width}; height: {place.height};" onpointerdown={(e) => takeGrip(e, 'move')} onpointermove={pull} onpointerup={letGo}>
			{#if chosen.kind !== 'pin'}
				{#each ['nw', 'ne', 'sw', 'se'] as const as how (how)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<span class="handle {how}" data-testid="mark-handle-{how}" onpointerdown={(e) => takeGrip(e, how)} onpointermove={pull} onpointerup={letGo}></span>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.page-marks {
		position: absolute;
		inset: 0;
		z-index: 2;
		pointer-events: none;
	}
	.page-marks.drawing {
		z-index: 4;
		pointer-events: auto;
		cursor: crosshair;
		touch-action: none;
	}
	svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.bands {
		z-index: 1;
		pointer-events: none;
		mix-blend-mode: multiply;
	}
	/* The annotation neutral until its reader gives it a colour (A4), on the page's own white whatever the theme, so the words stay readable and the tint stays a tint. */
	.band {
		fill: var(--band, var(--ann-neutral));
		fill-opacity: var(--band-strength, 0.3);
	}
	.rule,
	.shape {
		fill: none;
		stroke: var(--line, var(--ann-neutral));
		stroke-width: 1.3;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.plain .rule,
	.plain .shape {
		stroke-width: 0.8;
		stroke-dasharray: 2 2;
	}
	.m.on .band {
		stroke: var(--line, var(--ann-neutral));
		stroke-width: 0.8;
	}
	.m.on .rule,
	.m.on .shape {
		stroke: var(--line, var(--accent));
		stroke-width: 2;
	}
	.hit,
	.embedded {
		position: absolute;
		display: block;
		border: 0;
		padding: 0;
		background: transparent;
		pointer-events: none;
	}
	.hit:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 1px;
	}
	.hit.pin,
	.hit.words {
		pointer-events: auto;
		cursor: pointer;
		color: var(--line, var(--ann-neutral));
	}
	.idle .hit.pin,
	.idle .hit.words {
		pointer-events: none;
	}
	.hit.pin :global(svg) {
		position: static;
		width: 100%;
		height: 100%;
		fill: var(--band, #fff);
	}
	.hit.pin.on {
		color: var(--line, var(--accent));
	}
	/* words on the page, set on the page's white in a dark ink whatever the theme, as they are in a saved copy */
	.hit.words {
		font-family: Helvetica, Arial, sans-serif;
		line-height: 1.2;
		text-align: left;
		white-space: pre-wrap;
		overflow: visible;
		color: var(--line, #3c3c42);
	}
	.hit.words.on {
		outline: 1px dashed var(--accent);
	}
	.grab {
		position: absolute;
		z-index: 1;
		pointer-events: auto;
		cursor: move;
		touch-action: none;
		outline: 1px dashed var(--accent);
		outline-offset: 2px;
	}
	.idle .grab {
		display: none;
	}
	.handle {
		position: absolute;
		width: 9px;
		height: 9px;
		background: var(--surface, #fff);
		border: 1.5px solid var(--accent);
		border-radius: 2px;
	}
	.handle.nw {
		left: -6px;
		top: -6px;
		cursor: nwse-resize;
	}
	.handle.ne {
		right: -6px;
		top: -6px;
		cursor: nesw-resize;
	}
	.handle.sw {
		left: -6px;
		bottom: -6px;
		cursor: nesw-resize;
	}
	.handle.se {
		right: -6px;
		bottom: -6px;
		cursor: nwse-resize;
	}
</style>
