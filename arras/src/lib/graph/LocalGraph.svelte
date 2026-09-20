<script lang="ts">
	// The local graph (book 15.5.1): one node's neighbourhood, drawn live, in the manner of Quartz's graph view. The centre is pinned in the middle and its neighbours settle around it, so when the centre moves — a reader scrolling on — nodes that stay in view keep their places and only the arrivals move.
	// Hovering a node dims everything but it and its neighbours; each node is a link, so a click opens it and a rest shows its preview. Drawn in SVG with d3-force, which the viewer already carries, rather than ported with Quartz's PixiJS renderer: a neighbourhood is tens of nodes, and arras ships inside loom's wheel.
	import { onDestroy } from 'svelte';
	import { forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type Simulation, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force';
	import { store } from '$lib/manifest/client.svelte';
	import { colorOf } from './layout';
	import { neighbourhood, shortLabel } from './local';
	import { toneClass } from '$lib/state';
	import { keyUrl } from '$lib/nav';

	let {
		center,
		depth = 1,
		height = 200,
		master = undefined,
		hrefFor = undefined,
		allLabels = false
	}: {
		center: string;
		depth?: number;
		height?: number;
		/** The document being read, for numbering the labels. */
		master?: string;
		/** Where a node's link goes; defaults to its page. The read view passes an in-document jump for the nodes it holds. */
		hrefFor?: (id: string) => string;
		/** Label every node, as the expanded drawing does, rather than only the centre and whatever is hovered. */
		allLabels?: boolean;
	} = $props();

	interface SimNode extends SimulationNodeDatum {
		id: string;
		r: number;
	}
	type SimLink = SimulationLinkDatum<SimNode> & { kind: string; from: string; to: string };

	const m = $derived(store.manifest);
	let width = $state(0);
	let frame = $state(0);
	let hover = $state('');
	let k = $state(1);
	let tx = $state(0);
	let ty = $state(0);
	let nodes = $state.raw<SimNode[]>([]);
	let links = $state.raw<SimLink[]>([]);
	let svg: SVGSVGElement | undefined = $state();
	const known = new Map<string, SimNode>();
	let sim: Simulation<SimNode, SimLink> | null = null;

	const neighbours = $derived.by(() => {
		const out = new Map<string, Set<string>>();
		for (const l of links) {
			(out.get(l.from) ?? out.set(l.from, new Set()).get(l.from)!).add(l.to);
			(out.get(l.to) ?? out.set(l.to, new Set()).get(l.to)!).add(l.from);
		}
		return out;
	});

	$effect(() => {
		const mm = m;
		const c = center;
		const d = depth;
		if (!mm || !c) return;
		const hood = neighbourhood(mm, c, d);
		const degree = new Map<string, number>();
		for (const l of hood.links) {
			degree.set(l.from, (degree.get(l.from) ?? 0) + 1);
			degree.set(l.to, (degree.get(l.to) ?? 0) + 1);
		}
		const centreId = hood.nodes[0];
		const next: SimNode[] = hood.nodes.map((id) => {
			let n = known.get(id);
			if (!n) {
				// an arrival starts beside something already placed that it is linked to, so it grows out of the drawing rather than flying in from the origin
				const anchor = hood.links.map((l) => (l.from === id ? l.to : l.to === id ? l.from : '')).find((o) => o && known.has(o));
				const a = anchor ? known.get(anchor)! : { x: 0, y: 0 };
				n = { id, r: 4, x: (a.x ?? 0) + (Math.random() - 0.5) * 30, y: (a.y ?? 0) + (Math.random() - 0.5) * 30 };
				known.set(id, n);
			}
			n.r = 3.5 + Math.sqrt(degree.get(id) ?? 0) * 1.6 + (id === centreId ? 2 : 0);
			n.fx = id === centreId ? 0 : null;
			n.fy = id === centreId ? 0 : null;
			return n;
		});
		for (const id of [...known.keys()]) if (!hood.distance.has(id)) known.delete(id);
		const nextLinks: SimLink[] = hood.links.map((l) => ({ ...l, source: l.from, target: l.to }));
		nodes = next;
		links = nextLinks;
		if (!sim) {
			sim = forceSimulation<SimNode, SimLink>()
				.force('charge', forceManyBody<SimNode>().strength(-110).distanceMax(260))
				.force('x', forceX<SimNode>(0).strength(0.05))
				.force('y', forceY<SimNode>(0).strength(0.05))
				.alphaDecay(0.035)
				.on('tick', () => {
					fit();
					frame++;
				});
		}
		sim.nodes(next);
		sim.force('link', forceLink<SimNode, SimLink>(nextLinks).id((n) => n.id).distance(46).strength(0.7));
		sim.force('collide', forceCollide<SimNode>((n) => n.r + 3));
		// a new centre is a new question, so the drawing fits itself again even if the reader had zoomed the last one
		placed = false;
		sim.alpha(0.8).restart();
	});

	/** Whether the reader has zoomed or panned; until they do, the drawing keeps itself fitted to the box as it settles. */
	let placed = false;
	function fit() {
		if (placed || !nodes.length || !width) return;
		let x0 = Infinity;
		let y0 = Infinity;
		let x1 = -Infinity;
		let y1 = -Infinity;
		for (const n of nodes) {
			x0 = Math.min(x0, (n.x ?? 0) - n.r);
			y0 = Math.min(y0, (n.y ?? 0) - n.r);
			x1 = Math.max(x1, (n.x ?? 0) + n.r);
			y1 = Math.max(y1, (n.y ?? 0) + n.r + 12);
		}
		// labels hang wider than their dots, so the sides get more room than the top and bottom; a small neighbourhood is enlarged only so far, since the dots and strokes grow with it
		const padX = 56;
		const padY = 20;
		const next = Math.min(1.6, Math.max(0.4, Math.min(width / (x1 - x0 + padX * 2), height / (y1 - y0 + padY * 2))));
		k = next;
		tx = -((x0 + x1) / 2) * next;
		ty = -((y0 + y1) / 2) * next;
	}

	onDestroy(() => sim?.stop());

	const centreId = $derived(nodes[0]?.id ?? '');
	const href = (id: string) => (hrefFor ? hrefFor(id) : keyUrl(m, id));
	const lit = (id: string) => !hover || id === hover || !!neighbours.get(hover)?.has(id);
	const labelled = (id: string) => allLabels || k > 1.8 || id === centreId || id === hover || (!!hover && !!neighbours.get(hover)?.has(id));

	/** Pointer position in drawing coordinates, through the screen matrix of the zoomed group's parent. */
	function toDrawing(ev: { clientX: number; clientY: number }) {
		const ctm = svg?.getScreenCTM();
		if (!ctm) return { x: 0, y: 0 };
		const p = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(ctm.inverse());
		return { x: (p.x - tx) / k, y: (p.y - ty) / k };
	}

	let drag: { node?: SimNode; x: number; y: number; moved: boolean } | null = null;
	let suppressClick = false;

	function down(ev: PointerEvent, node?: SimNode) {
		const p = toDrawing(ev);
		drag = { node, x: p.x, y: p.y, moved: false };
		(ev.currentTarget as Element).setPointerCapture?.(ev.pointerId);
		if (node) ev.stopPropagation();
	}
	function move(ev: PointerEvent) {
		if (!drag) return;
		const p = toDrawing(ev);
		if (Math.abs(p.x - drag.x) + Math.abs(p.y - drag.y) > 3) drag.moved = true;
		if (!drag.moved) return;
		if (drag.node) {
			drag.node.fx = p.x;
			drag.node.fy = p.y;
			sim?.alphaTarget(0.3).restart();
		} else {
			placed = true;
			tx += (p.x - drag.x) * k;
			ty += (p.y - drag.y) * k;
		}
	}
	function up() {
		if (drag?.node) {
			if (drag.node.id !== centreId) {
				drag.node.fx = null;
				drag.node.fy = null;
			}
			sim?.alphaTarget(0);
		}
		suppressClick = !!drag?.moved;
		drag = null;
	}
	function wheel(ev: WheelEvent) {
		ev.preventDefault();
		const ctm = svg?.getScreenCTM();
		if (!ctm) return;
		const p = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(ctm.inverse());
		placed = true;
		const next = Math.min(4, Math.max(0.4, k * Math.exp(-ev.deltaY / 300)));
		tx = p.x - ((p.x - tx) * next) / k;
		ty = p.y - ((p.y - ty) * next) / k;
		k = next;
	}
	function click(ev: MouseEvent) {
		if (suppressClick) {
			ev.preventDefault();
			suppressClick = false;
		}
	}
	const pos = (n: SimNode | string | number | undefined) => (typeof n === 'object' && n ? { x: n.x ?? 0, y: n.y ?? 0 } : { x: 0, y: 0 });

	// d3 moves the node objects in place, which no reactive read can see, so each tick copies out what is drawn
	const drawnNodes = $derived.by(() => {
		void frame;
		return nodes.map((n) => ({ id: n.id, x: n.x ?? 0, y: n.y ?? 0, r: n.r, sim: n }));
	});
	const drawnLinks = $derived.by(() => {
		void frame;
		return links.map((l) => {
			const a = pos(l.source as SimNode);
			const b = pos(l.target as SimNode);
			return { key: l.from + '>' + l.to + l.kind, from: l.from, to: l.to, kind: l.kind, x1: a.x, y1: a.y, x2: b.x, y2: b.y };
		});
	});
</script>

<div class="local-graph" bind:clientWidth={width} style="height: {height}px" data-testid="local-graph" data-preview-side="left">
	{#if m && nodes.length}
		<svg
			bind:this={svg}
			viewBox="{-width / 2} {-height / 2} {width || 1} {height}"
			width="100%"
			{height}
			role="img"
			aria-label="the neighbourhood of {centreId}: {nodes.length} nodes"
			onpointerdown={(e) => down(e)}
			onpointermove={move}
			onpointerup={up}
			onpointercancel={up}
			onwheel={wheel}
		>
			<g transform="translate({tx},{ty}) scale({k})">
				{#each drawnLinks as l (l.key)}
					<line x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2} class="link kind-{l.kind}" class:lit={!!hover && (l.from === hover || l.to === hover)} class:dim={!!hover && l.from !== hover && l.to !== hover} />
				{/each}
				{#each drawnNodes as n (n.id)}
					{@const node = m.nodes[n.id]}
					<a href={href(n.id)} data-preview-key={n.id} onclick={click} onpointerdown={(e) => down(e, n.sim)} onpointerenter={() => (hover = n.id)} onpointerleave={() => (hover = hover === n.id ? '' : hover)} aria-label={shortLabel(m, n.id, master)}>
						<circle cx={n.x} cy={n.y} r={n.r} class="dot {toneClass(colorOf(m, node?.state ?? ''))}" class:centre={n.id === centreId} class:external={node?.external} class:dim={!lit(n.id)} />
						{#if labelled(n.id)}
							<text x={n.x} y={n.y + n.r + 9} class="label" class:dim={!lit(n.id)} font-size={10 / Math.max(1, k * 0.8)}>{shortLabel(m, n.id, master)}</text>
						{/if}
					</a>
				{/each}
			</g>
		</svg>
		{#if nodes.length === 1}<p class="alone">nothing depends on this, and it depends on nothing</p>{/if}
	{:else}
		<p class="alone">nothing to draw</p>
	{/if}
</div>

<style>
	.local-graph {
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
	.link {
		stroke: var(--rule-strong);
		stroke-width: 1;
		transition: opacity 120ms;
	}
	.link.kind-proof {
		stroke-dasharray: 3 2;
	}
	.link.kind-prose,
	.link.kind-see {
		stroke-dasharray: 1 2.5;
	}
	.link.lit {
		stroke: var(--link);
		stroke-width: 1.4;
	}
	.dot {
		fill: color-mix(in srgb, var(--tone) 55%, var(--sheet));
		stroke: var(--tone);
		stroke-width: 1;
		cursor: pointer;
		transition: opacity 120ms;
	}
	.dot.external {
		fill: var(--sheet);
		stroke-dasharray: 2 1.5;
	}
	.dot.centre {
		fill: var(--link);
		stroke: var(--link);
		stroke-width: 3;
		stroke-opacity: 0.25;
	}
	.label {
		font-family: var(--sans);
		fill: var(--ink-soft);
		text-anchor: middle;
		pointer-events: none;
		paint-order: stroke;
		stroke: var(--sheet);
		stroke-width: 3px;
		stroke-linejoin: round;
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
