<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { closureOf, downstream, layout, type Layout } from '$lib/graph/layout';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	let master = $state('');
	let taxon = $state('');
	let tag = $state('');
	let hideExternal = $state(false);
	let selected = $state('');
	let mode = $state<'downstream' | 'closure'>('downstream');
	let laid = $state<Layout | null>(null);
	let error = $state('');

	const highlighted = $derived.by(() => {
		if (!selected || !m) return new Set<string>();
		return mode === 'downstream' ? downstream(m, selected) : closureOf(m, selected);
	});

	$effect(() => {
		const hash = store.hash;
		const f = { master: master || undefined, taxon: taxon || undefined, tag: tag || undefined, hideExternal };
		if (!hash) return;
		layout(m, f)
			.then((l) => {
				laid = l;
				error = '';
			})
			.catch((e) => (error = String(e)));
	});

	function path(points: { x: number; y: number }[]): string {
		return points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
	}
	const taxa = $derived(Object.keys(m.taxa).sort());
	const tags = $derived(Object.keys(m.tags).sort());
</script>

<main class="page graph">
	<h1>Graph</h1>
	<p class="controls">
		<label>master <select bind:value={master}><option value="">all</option>{#each m.masters as x (x.path)}<option value={x.path}>{x.path}</option>{/each}</select></label>
		<label>taxon <select bind:value={taxon}><option value="">all</option>{#each taxa as t (t)}<option value={t}>{t}</option>{/each}</select></label>
		<label>tag <select bind:value={tag}><option value="">all</option>{#each tags as t (t)}<option value={t}>{t}</option>{/each}</select></label>
		<label><input type="checkbox" bind:checked={hideExternal} /> hide external</label>
		<label>highlight <select bind:value={mode}><option value="downstream">downstream</option><option value="closure">closure</option></select></label>
		{#if selected}<span>of <code>{selected}</code> <button type="button" onclick={() => (selected = '')}>clear</button></span>{/if}
	</p>
	{#if error}
		<p class="problem">{error}</p>
	{:else if !laid}
		<p class="muted">Laying out…</p>
	{:else}
		<p class="muted">solid: statement-edges · dashed: proof-edges · dotted: prose-edges · boxes group nodes by section · click a node to highlight, double-click to open</p>
		<div class="scroll">
			<svg width={laid.width + 20} height={laid.height + 20} viewBox="-10 -10 {laid.width + 20} {laid.height + 20}" role="img" aria-label="dependency graph">
				<defs>
					<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-soft)" /></marker>
				</defs>
				{#each laid.groups as g (g.id)}
					<rect x={g.x} y={g.y} width={g.w} height={g.h} class="group" rx="6" />
					<text x={g.x + 8} y={g.y + 18} class="group-label">{g.label}</text>
				{/each}
				{#each laid.edges as e, i (i)}
					<path d={path(e.points)} class="edge edge-{e.kind}" class:dim={selected && !highlighted.has(e.from) && e.from !== selected} marker-end="url(#arrow)" />
				{/each}
				{#each laid.nodes as n (n.id)}
					<g class="node" class:selected={n.id === selected} class:hl={highlighted.has(n.id)} class:dim={selected && !highlighted.has(n.id) && n.id !== selected} onclick={() => (selected = n.id)} ondblclick={() => (location.href = nodeUrl(n.id))} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && (selected = n.id)}>
						<rect x={n.x} y={n.y} width={n.w} height={n.h} rx={n.style === 'definition' ? 12 : n.style === 'remark' ? 0 : 4} class="fill-{n.color}" stroke-dasharray={n.external ? '4 2' : ''} />
						<text x={n.x + 8} y={n.y + 21}><tspan class="id">{n.id}</tspan> <tspan class="taxon">{n.taxon}</tspan></text>
					</g>
				{/each}
			</svg>
		</div>
	{/if}
</main>

<style>
	main.graph {
		max-width: none;
	}
	.controls label {
		margin-right: 1rem;
	}
	.scroll {
		overflow: auto;
		border: 1px solid var(--rule);
	}
	.group {
		fill: color-mix(in srgb, var(--link) 6%, transparent);
		stroke: var(--rule);
	}
	.group-label {
		font-size: 12px;
		fill: var(--ink-soft);
	}
	.edge {
		fill: none;
		stroke: var(--ink-soft);
		stroke-width: 1.3;
	}
	.edge-proof {
		stroke-dasharray: 5 3;
	}
	.edge-prose {
		stroke-dasharray: 1.5 3;
	}
	.node rect {
		stroke: var(--rule);
	}
	.node text {
		font-size: 12px;
		fill: var(--ink);
		pointer-events: none;
	}
	.node .taxon {
		fill: var(--ink-soft);
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
		fill: var(--state-incomplete);
	}
	.fill-info {
		fill: var(--link-wash);
	}
	.node.selected rect {
		stroke: var(--link);
		stroke-width: 2.5;
	}
	.node.hl rect {
		stroke: var(--link);
		stroke-width: 2;
	}
	.dim {
		opacity: 0.25;
	}
	.node {
		cursor: pointer;
	}
</style>
