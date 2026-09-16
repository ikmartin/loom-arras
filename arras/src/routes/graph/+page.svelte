<script lang="ts">
	// The graph (book 15.5): one page, two layouts, a toggle that keeps the selection, the filters and the scope. Pan, zoom and drag belong to both.
	import { store } from '$lib/manifest/client.svelte';
	import { closureOf, downstream, layout, type Layout } from '$lib/graph/layout';
	import { forceLayout, R } from '$lib/graph/force';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import PageRail from '$lib/shell/PageRail.svelte';
	import RailList from '$lib/components/RailList.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import { nodeBadge } from '$lib/badges';
	import { reachedExternal } from '$lib/reached';
	import { keyUrl, nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	let mode = $state<'force' | 'layered'>('force');
	let master = $state('');
	let taxon = $state('');
	let tag = $state('');
	let stateFilter = $state('');
	let external = $state<'reached' | 'all' | 'none'>('reached');
	let selected = $state('');
	let depth = $state(0);
	let highlight = $state<'downstream' | 'closure'>('downstream');
	let laid = $state<Layout | null>(null);
	let error = $state('');

	// Pan and zoom, as a viewBox transform; the previous drawing's positions seed the next so a filter change moves nodes rather than reshuffling them.
	let tx = $state(0);
	let ty = $state(0);
	let scale = $state(1);
	let dragging = $state<{ kind: 'pan' | 'node'; id?: string; x: number; y: number } | null>(null);
	let svgEl: SVGSVGElement | undefined = $state();
	let seed = new Map<string, { x: number; y: number }>();
	let moved = $state(new Map<string, { x: number; y: number }>());

	const reached = $derived(reachedExternal(m));
	const filters = $derived({ master: master || undefined, taxon: taxon || undefined, tag: tag || undefined, external, reached });

	const related = $derived.by(() => {
		if (!selected || !m) return new Set<string>();
		return highlight === 'downstream' ? downstream(m, selected) : closureOf(m, selected);
	});

	/** Nodes within `depth` steps of the selection, ignoring direction; 0 means the whole scope (15.5). */
	function inScope(l: Layout): Set<string> | null {
		if (!selected || depth === 0) return null;
		const adj = new Map<string, string[]>();
		for (const e of l.edges) {
			(adj.get(e.from) ?? adj.set(e.from, []).get(e.from)!).push(e.to);
			(adj.get(e.to) ?? adj.set(e.to, []).get(e.to)!).push(e.from);
		}
		const seen = new Set([selected]);
		let front = [selected];
		for (let d = 0; d < depth; d++) {
			const next: string[] = [];
			for (const id of front)
				for (const nb of adj.get(id) ?? [])
					if (!seen.has(nb)) {
						seen.add(nb);
						next.push(nb);
					}
			front = next;
		}
		return seen;
	}

	$effect(() => {
		const hash = store.hash;
		const f = filters;
		const mo = mode;
		if (!hash) return;
		if (mo === 'force') {
			try {
				// the seed is taken from the value, never from `laid`: reading state this effect has just written makes the effect depend on itself, which re-laid the graph hundreds of times per navigation
				const next = forceLayout(m, f, seed);
				seed = new Map(next.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
				laid = next;
				moved = new Map();
				error = '';
			} catch (e) {
				error = String(e);
			}
			return;
		}
		layout(m, f)
			.then((l) => {
				laid = l;
				moved = new Map();
				error = '';
			})
			.catch((e) => (error = String(e)));
	});

	const scope = $derived(laid ? inScope(laid) : null);
	const shown = $derived(laid ? laid.nodes.filter((n) => !scope || scope.has(n.id)) : []);
	const shownIds = $derived(new Set(shown.map((n) => n.id)));
	const shownEdges = $derived(laid ? laid.edges.filter((e) => shownIds.has(e.from) && shownIds.has(e.to)) : []);
	const at = (id: string, x: number, y: number) => moved.get(id) ?? { x, y };

	function path(points: { x: number; y: number }[], e: { from: string; to: string }): string {
		const pts = points.length === 2 ? [at(e.from, points[0].x, points[0].y), at(e.to, points[1].x, points[1].y)] : points;
		return pts.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
	}

	function toDiagram(ev: PointerEvent): { x: number; y: number } {
		const r = svgEl?.getBoundingClientRect();
		if (!r || !laid) return { x: 0, y: 0 };
		const vw = laid.width / scale;
		const vh = laid.height / scale;
		return { x: tx + ((ev.clientX - r.left) / r.width) * vw, y: ty + ((ev.clientY - r.top) / r.height) * vh };
	}

	function down(ev: PointerEvent, id?: string) {
		const p = toDiagram(ev);
		dragging = { kind: id ? 'node' : 'pan', id, x: p.x, y: p.y };
		(ev.currentTarget as Element).setPointerCapture?.(ev.pointerId);
	}
	function move(ev: PointerEvent) {
		if (!dragging || !laid) return;
		const p = toDiagram(ev);
		const dx = p.x - dragging.x;
		const dy = p.y - dragging.y;
		if (dragging.kind === 'pan') {
			tx -= dx;
			ty -= dy;
		} else if (dragging.id) {
			const n = laid.nodes.find((x) => x.id === dragging!.id);
			if (n) {
				const cur = moved.get(n.id) ?? { x: n.x, y: n.y };
				const next = new Map(moved);
				next.set(n.id, { x: cur.x + dx, y: cur.y + dy });
				moved = next;
			}
			dragging = { ...dragging, x: p.x, y: p.y };
		}
	}
	function up() {
		dragging = null;
	}
	function wheel(ev: WheelEvent) {
		ev.preventDefault();
		const k = Math.exp(-ev.deltaY / 400);
		scale = Math.min(6, Math.max(0.2, scale * k));
	}
	function reset() {
		tx = 0;
		ty = 0;
		scale = 1;
		moved = new Map();
	}

	const taxa = $derived(Object.keys(m.taxa).sort());
	const tags = $derived(Object.keys(m.tags).sort());
	const states = $derived(Object.keys(m.states.labels).sort());
	const node = $derived(selected ? m.nodes[selected] : undefined);
	const viewBox = $derived(laid ? `${tx} ${ty} ${laid.width / scale} ${laid.height / scale}` : '0 0 100 100');
	const stateOk = (id: string) => !stateFilter || m.nodes[id]?.state === stateFilter;
</script>

<main class="page graph">
	<header class="head">
		<h1>Graph</h1>
		<div class="toggle" role="group" aria-label="Layout">
			<button class:on={mode === 'force'} aria-pressed={mode === 'force'} onclick={() => (mode = 'force')} data-testid="layout-force">force</button>
			<button class:on={mode === 'layered'} aria-pressed={mode === 'layered'} onclick={() => (mode = 'layered')} data-testid="layout-layered">layered</button>
		</div>
		<button class="as-link" onclick={reset}>reset view</button>
	</header>

	{#if error}
		<p class="problem">{error}</p>
	{:else if !laid}
		<p class="faint">Laying out…</p>
	{:else}
		<p class="faint">
			{shown.length} nodes · {shownEdges.length} edges · solid statement, dashed proof, dotted prose · drag to pan, scroll to zoom, drag a node to move it, click to select, double-click to open
		</p>
		<div class="canvas">
			<svg
				bind:this={svgEl}
				{viewBox}
				role="application"
				aria-label="dependency graph"
				class:layered={mode === 'layered'}
				onpointerdown={(e) => down(e)}
				onpointermove={move}
				onpointerup={up}
				onpointerleave={up}
				onwheel={wheel}
			>
				<defs>
					<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
						<path d="M0,0 L10,5 L0,10 z" fill="var(--ink-faint)" />
					</marker>
				</defs>
				{#if mode === 'layered'}
					{#each laid.groups as g (g.id)}
						<rect x={g.x} y={g.y} width={g.w} height={g.h} class="group" rx="6" />
						<text x={g.x + 8} y={g.y + 18} class="group-label">{g.label}</text>
					{/each}
				{/if}
				{#each shownEdges as e, i (i)}
					<path
						d={path(e.points, e)}
						class="edge edge-{e.kind}"
						class:dim={selected && !related.has(e.from) && e.from !== selected}
						marker-end={mode === 'layered' ? 'url(#arrow)' : undefined}
					/>
				{/each}
				{#each shown as n (n.id)}
					{@const p = at(n.id, n.x, n.y)}
					<g
						class="node"
						class:selected={n.id === selected}
						class:hl={related.has(n.id)}
						class:dim={(selected && !related.has(n.id) && n.id !== selected) || !stateOk(n.id)}
						onpointerdown={(e) => {
							e.stopPropagation();
							down(e, n.id);
						}}
						onclick={() => (selected = n.id)}
						ondblclick={() => (location.href = nodeUrl(n.id))}
						role="button"
						tabindex="0"
						onkeydown={(e) => e.key === 'Enter' && (selected = n.id)}
						data-testid="gnode-{n.id}"
					>
						{#if mode === 'force'}
							<circle cx={p.x} cy={p.y} r={n.id === selected ? R * 1.7 : n.section ? R * 1.3 : R} class="fill-{n.color}" stroke-dasharray={n.external ? '3 2' : ''} />
							<text x={p.x} y={p.y + R + 10} class="under">{n.id}</text>
						{:else}
							<rect x={p.x} y={p.y} width={n.w} height={n.h} rx={n.style === 'definition' ? 12 : n.style === 'remark' ? 0 : 4} class="fill-{n.color}" stroke-dasharray={n.external ? '4 2' : ''} />
							<text x={p.x + 8} y={p.y + 21}><tspan class="id">{n.id}</tspan> <tspan class="taxon">{n.taxon}</tspan></text>
						{/if}
					</g>
				{/each}
			</svg>
		</div>
	{/if}
</main>

<PagePanel label="Graph">
	<div class="filters">
		<label>document<select bind:value={master}><option value="">all</option>{#each m.masters as x (x.path)}<option value={x.path}>{x.path}</option>{/each}</select></label>
		<label>taxon<select bind:value={taxon}><option value="">all</option>{#each taxa as t (t)}<option value={t}>{t}</option>{/each}</select></label>
		<label>tag<select bind:value={tag}><option value="">all</option>{#each tags as t (t)}<option value={t}>{t}</option>{/each}</select></label>
		<label>state<select bind:value={stateFilter}><option value="">all</option>{#each states as t (t)}<option value={t}>{t}</option>{/each}</select></label>
		<label>depth around selection<select bind:value={depth}><option value={0}>whole scope</option><option value={1}>1</option><option value={2}>2</option><option value={3}>3</option></select></label>
		<label>highlight<select bind:value={highlight}><option value="downstream">what rests on it</option><option value="closure">what it rests on</option></select></label>
		<label>cited results<select bind:value={external}><option value="reached">used here</option><option value="all">all</option><option value="none">none</option></select></label>
	</div>
</PagePanel>

{#if node}
	<PageRail>
		<RailList label="selected">
			<p class="sel"><a href={keyUrl(m, selected)}>{node.taxon}{node.title ? ' · ' + node.title : ''}</a></p>
			<p><Badge parts={nodeBadge(m, node)} /></p>
			<p class="faint">{related.size} {highlight === 'downstream' ? 'rest on it' : 'it rests on'}</p>
			<p><button class="as-link" onclick={() => (selected = '')}>clear</button></p>
		</RailList>
	</PageRail>
{/if}

<style>
	main.graph {
		display: flex;
		flex-direction: column;
		height: 100vh;
		padding-bottom: 0;
	}
	.head {
		display: flex;
		align-items: baseline;
		gap: var(--gap);
	}
	.toggle {
		display: flex;
		gap: 2px;
	}
	.toggle button {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 2px 9px;
		cursor: pointer;
	}
	.toggle button.on {
		background: var(--link-wash);
		border-color: var(--link);
		color: var(--link);
	}
	.canvas {
		flex: 1;
		min-height: 0;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		overflow: hidden;
		background: var(--sheet);
		margin-bottom: var(--gap-wide);
	}
	svg {
		width: 100%;
		height: 100%;
		touch-action: none;
		cursor: grab;
	}
	.group {
		fill: color-mix(in srgb, var(--link) 6%, transparent);
		stroke: var(--rule);
	}
	.group-label {
		font-family: var(--sans);
		font-size: 11px;
		fill: var(--ink-faint);
	}
	.edge {
		fill: none;
		stroke: var(--rule-strong);
		stroke-width: 1.1;
	}
	.edge-proof {
		stroke-dasharray: 5 3;
	}
	.edge-prose {
		stroke-dasharray: 1.5 3;
	}
	.node {
		cursor: pointer;
	}
	.node circle,
	.node rect {
		stroke: var(--rule-strong);
		transition: r 140ms, cx 220ms, cy 220ms;
	}
	.node text {
		font-family: var(--sans);
		font-size: 10px;
		fill: var(--ink-soft);
		pointer-events: none;
	}
	.node text.under {
		text-anchor: middle;
	}
	.node .taxon {
		fill: var(--ink-faint);
	}
	.fill-neutral {
		fill: var(--state-draft-wash);
	}
	.fill-positive {
		fill: var(--state-accepted-wash);
	}
	.fill-positive-strong {
		fill: var(--state-accepted);
	}
	.fill-warning {
		fill: var(--state-stale-wash);
	}
	.fill-negative {
		fill: var(--state-incomplete-wash);
	}
	.fill-info {
		fill: var(--link-wash);
	}
	.node.selected circle,
	.node.selected rect {
		stroke: var(--link);
		stroke-width: 2.5;
	}
	.node.hl circle,
	.node.hl rect {
		stroke: var(--link);
		stroke-width: 2;
	}
	.dim {
		opacity: 0.22;
	}
	.filters {
		display: grid;
		gap: var(--gap-tight);
	}
	.filters label {
		display: grid;
		gap: 2px;
		font-family: var(--sans);
		font-size: 9px;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	.sel {
		font-size: 12px;
		margin: 0 0 var(--gap-hair);
	}
</style>
