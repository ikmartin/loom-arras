<script lang="ts">
	// The local graph as boxes (book 15.5.1): the neighbourhood the dot drawing shows, laid out in layers with what a result rests on above it. Pan and zoom as in the dot drawing; nothing is dragged, since a layered drawing's positions are its meaning.
	import { store } from '$lib/manifest/client.svelte';
	import { colorOf } from './layout';
	import { neighbourhood } from './local';
	import { boxLayout, type BoxDrawing } from './localbox';
	import { toneClass } from '$lib/state';
	import { keyUrl } from '$lib/nav';

	let {
		center,
		depth = 1,
		height = 200,
		master = undefined,
		hrefFor = undefined
	}: {
		center: string;
		depth?: number;
		height?: number;
		master?: string;
		hrefFor?: (id: string) => string;
	} = $props();

	const m = $derived(store.manifest);
	let width = $state(0);
	let drawing = $state.raw<BoxDrawing | null>(null);
	let hover = $state('');
	let k = $state(1);
	let tx = $state(0);
	let ty = $state(0);
	let placed = false;
	let svg: SVGSVGElement | undefined = $state();

	$effect(() => {
		const mm = m;
		const c = center;
		const d = depth;
		const doc = master;
		if (!mm || !c) return;
		let live = true;
		boxLayout(mm, neighbourhood(mm, c, d), doc).then((next) => {
			if (!live) return;
			drawing = next;
			placed = false;
		});
		return () => {
			live = false;
		};
	});

	// fitted to the box until the reader zooms or pans; a small neighbourhood is enlarged only so far
	$effect(() => {
		const dr = drawing;
		const w = width;
		if (!dr || !w || placed) return;
		const next = Math.min(1.4, Math.max(0.3, Math.min((w - 12) / Math.max(1, dr.width), (height - 12) / Math.max(1, dr.height))));
		k = next;
		tx = (w - dr.width * next) / 2;
		ty = (height - dr.height * next) / 2;
	});

	const centreId = $derived(drawing?.nodes.find((n) => n.id === (m?.keys[center]?.node ?? center))?.id ?? '');
	const neighbours = $derived.by(() => {
		const out = new Map<string, Set<string>>();
		for (const e of drawing?.edges ?? []) {
			(out.get(e.from) ?? out.set(e.from, new Set()).get(e.from)!).add(e.to);
			(out.get(e.to) ?? out.set(e.to, new Set()).get(e.to)!).add(e.from);
		}
		return out;
	});
	const lit = (id: string) => !hover || id === hover || !!neighbours.get(hover)?.has(id);
	const href = (id: string) => (hrefFor ? hrefFor(id) : keyUrl(m, id));
	const path = (pts: { x: number; y: number }[]) => pts.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');

	let drag: { x: number; y: number; moved: boolean } | null = null;
	let suppressClick = false;
	function down(ev: PointerEvent) {
		drag = { x: ev.clientX, y: ev.clientY, moved: false };
		(ev.currentTarget as Element).setPointerCapture?.(ev.pointerId);
	}
	function move(ev: PointerEvent) {
		if (!drag) return;
		const dx = ev.clientX - drag.x;
		const dy = ev.clientY - drag.y;
		if (!drag.moved && Math.abs(dx) + Math.abs(dy) <= 3) return;
		drag.moved = true;
		placed = true;
		tx += dx;
		ty += dy;
		drag.x = ev.clientX;
		drag.y = ev.clientY;
	}
	function up() {
		suppressClick = !!drag?.moved;
		drag = null;
	}
	function wheel(ev: WheelEvent) {
		ev.preventDefault();
		const r = svg?.getBoundingClientRect();
		if (!r) return;
		const px = ev.clientX - r.left;
		const py = ev.clientY - r.top;
		placed = true;
		const next = Math.min(4, Math.max(0.3, k * Math.exp(-ev.deltaY / 300)));
		tx = px - ((px - tx) * next) / k;
		ty = py - ((py - ty) * next) / k;
		k = next;
	}
	function click(ev: MouseEvent) {
		if (suppressClick) {
			ev.preventDefault();
			suppressClick = false;
		}
	}
</script>

<div class="local-box" bind:clientWidth={width} style="height: {height}px" data-testid="local-graph-box" data-preview-side="left">
	{#if m && drawing && drawing.nodes.length}
		<svg bind:this={svg} width="100%" {height} role="img" aria-label="the neighbourhood of {centreId} as boxes: {drawing.nodes.length} nodes" onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up} onwheel={wheel}>
			<defs>
				<marker id="local-box-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
					<path d="M0,0 L10,5 L0,10 z" fill="var(--ink-faint)" />
				</marker>
			</defs>
			<g transform="translate({tx},{ty}) scale({k})">
				{#each drawing.edges as e, i (i)}
					<path d={path(e.points)} class="edge kind-{e.kind}" class:lit={!!hover && (e.from === hover || e.to === hover)} class:dim={!!hover && e.from !== hover && e.to !== hover} marker-end="url(#local-box-arrow)" />
				{/each}
				{#each drawing.nodes as n (n.id)}
					{@const node = m.nodes[n.id]}
					<a href={href(n.id)} data-preview-key={n.id} onclick={click} onpointerenter={() => (hover = n.id)} onpointerleave={() => (hover = hover === n.id ? '' : hover)} aria-label={n.label}>
						<rect x={n.x} y={n.y} width={n.w} height={n.h} rx={node?.style === 'definition' ? 9 : node?.style === 'remark' ? 0 : 3} class="box {toneClass(colorOf(m, node?.state ?? ''))}" class:centre={n.id === centreId} class:external={node?.external} class:dim={!lit(n.id)} />
						<text x={n.x + n.w / 2} y={n.y + n.h / 2 + 3.5} class="label" class:dim={!lit(n.id)}>{n.label}</text>
					</a>
				{/each}
			</g>
		</svg>
	{:else if m && drawing}
		<p class="alone">nothing to draw</p>
	{/if}
</div>

<style>
	.local-box {
		position: relative;
		width: 100%;
		overflow: hidden;
		border-radius: var(--rad-control);
		background: var(--sheet);
	}
	svg {
		display: block;
		touch-action: none;
		cursor: grab;
		user-select: none;
	}
	.edge {
		fill: none;
		stroke: var(--rule-strong);
		stroke-width: 1;
		transition: opacity 120ms;
	}
	.edge.kind-proof {
		stroke-dasharray: 3 2;
	}
	.edge.kind-prose,
	.edge.kind-see {
		stroke-dasharray: 1 2.5;
	}
	.edge.lit {
		stroke: var(--link);
		stroke-width: 1.4;
	}
	.box {
		fill: color-mix(in srgb, var(--tone) 30%, var(--sheet));
		stroke: var(--tone);
		stroke-width: 1;
		cursor: pointer;
		transition: opacity 120ms;
	}
	.box.external {
		fill: var(--sheet);
		stroke-dasharray: 3 2;
	}
	.box.centre {
		stroke: var(--link);
		stroke-width: 2.2;
	}
	.label {
		font-family: var(--sans);
		font-size: 10px;
		fill: var(--ink);
		text-anchor: middle;
		pointer-events: none;
	}
	.dim {
		opacity: 0.2;
	}
	.alone {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 6px;
		margin: 0;
		text-align: center;
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		pointer-events: none;
	}
</style>
