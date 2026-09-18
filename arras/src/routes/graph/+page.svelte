<script lang="ts">
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	// The graph (book 15.5): one page, four drawings of one filtered graph — Dots, Box, Sections and Reading Order — with the selection, the filters and the scope kept across them. Pan and zoom belong to the three laid-out drawings; dragging a node belongs to Dots alone, since a laid-out drawing's positions are its meaning, and Reading Order scrolls like the document it follows.
	import { store } from '$lib/manifest/client.svelte';
	import { closureOf, downstream, layout, PAPER, type Layout } from '$lib/graph/layout';
	import { sectionLayout, type Sections } from '$lib/graph/sections';
	import { readingOrder, type Reading } from '$lib/graph/reading';
	import { forceLayout, R } from '$lib/graph/force';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import PageRail from '$lib/shell/PageRail.svelte';
	import RailList from '$lib/components/RailList.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import { nodeBadge } from '$lib/badges';
	import { reachedExternal } from '$lib/reached';
	import { digestUrl, keyUrl, nodeUrl } from '$lib/nav';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import { bibText } from '$lib/works';

	type Mode = 'dots' | 'box' | 'sections' | 'reading';

	const m = $derived(store.manifest!);
	let mode = $state<Mode>('dots');
	let master = $state('');
	let taxon = $state('');
	let tag = $state('');
	let stateFilter = $state('');
	let external = $state<'reached' | 'all' | 'none' | 'papers'>('reached');
	let selected = $state('');
	let depth = $state(0);
	let highlight = $state<'downstream' | 'closure'>('downstream');
	let laid = $state<Layout | null>(null);
	// which drawing `laid` holds: ELK answers asynchronously, and until it does the drawing on screen is still the previous one, so shapes follow this rather than the toggle
	let laidMode = $state<Mode>('dots');
	let cards = $state<Sections | null>(null);
	let error = $state('');
	let hover = $state('');

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
		// a paper drawn as one node is no key of the manifest's; what rests on it is what the drawing joins to it
		if (selected.startsWith(PAPER)) return new Set((laid?.edges ?? []).filter((e) => e.to === selected).map((e) => e.from));
		return highlight === 'downstream' ? downstream(m, selected) : closureOf(m, selected);
	});
	const paper = $derived(selected.startsWith(PAPER) ? m.references[selected.slice(PAPER.length)] : undefined);
	const open = (id: string) => (id.startsWith(PAPER) ? digestUrl(id.slice(PAPER.length)) : nodeUrl(id));

	/** Nodes within `depth` steps of the selection in the corpus's dependency graph, ignoring direction; 0 means the whole scope (15.5). */
	const scope = $derived.by(() => {
		if (!selected || depth === 0 || !m) return null;
		const stmtOf = (key: string) => m.keys[key]?.node ?? key;
		const adj = new Map<string, string[]>();
		for (const e of m.edges) {
			const a = stmtOf(e.from);
			const b = stmtOf(e.to);
			(adj.get(a) ?? adj.set(a, []).get(a)!).push(b);
			(adj.get(b) ?? adj.set(b, []).get(b)!).push(a);
		}
		for (const e of laid?.edges ?? []) {
			// the work graph's paper nodes are the drawing's, not the manifest's
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
	});

	$effect(() => {
		const hash = store.hash;
		const f = filters;
		const mo = mode;
		if (!hash) return;
		if (mo === 'dots') {
			try {
				// the seed is taken from the value, never from `laid`: reading state this effect has just written makes the effect depend on itself, which re-laid the graph hundreds of times per navigation
				const next = forceLayout(m, f, seed);
				seed = new Map(next.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
				laid = next;
				laidMode = 'dots';
				moved = new Map();
				error = '';
			} catch (e) {
				error = String(e);
			}
			return;
		}
		if (mo === 'reading') {
			laidMode = 'reading';
			error = '';
			return;
		}
		if (mo === 'sections') {
			sectionLayout(m, f)
				.then((s) => {
					if (mode !== 'sections') return; // toggled away while ELK was working
					cards = s;
					laidMode = 'sections';
					error = '';
				})
				.catch((e) => (error = String(e)));
			return;
		}
		layout(m, f)
			.then((l) => {
				if (mode !== 'box') return;
				laid = l;
				laidMode = 'box';
				moved = new Map();
				error = '';
			})
			.catch((e) => (error = String(e)));
	});

	const reading = $derived<Reading | null>(mode === 'reading' && m ? readingOrder(m, filters) : null);
	const shown = $derived(laid ? laid.nodes.filter((n) => !scope || scope.has(n.id)) : []);
	const shownIds = $derived(new Set(shown.map((n) => n.id)));
	const shownEdges = $derived(laid ? laid.edges.filter((e) => shownIds.has(e.from) && shownIds.has(e.to)) : []);
	const at = (id: string, x: number, y: number) => moved.get(id) ?? { x, y };
	const drawing = $derived(laidMode === 'sections' ? cards : laid);
	const counts = $derived.by(() => {
		if (laidMode === 'sections') return `${cards?.cards.length ?? 0} sections · ${cards?.edges.length ?? 0} lines`;
		if (laidMode === 'reading') return `${reading?.rows.length ?? 0} rows · ${reading?.arcs.length ?? 0} arcs`;
		return `${shown.length} nodes · ${shownEdges.length} edges`;
	});
	const caption = $derived(
		{
			dots: 'no direction encoded; drag a node to move it',
			box: 'what a result rests on sits above it; sections are not drawn, and the references that run from one are left out with them',
			sections: 'one card per section, its results in reading order; a line carries every dependency between two sections, thicker for more',
			reading: 'the document top to bottom, with dependencies as arcs reaching back to what a result rests on'
		}[laidMode]
	);

	function path(points: { x: number; y: number }[], e: { from: string; to: string }): string {
		const pts = points.length === 2 ? [at(e.from, points[0].x, points[0].y), at(e.to, points[1].x, points[1].y)] : points;
		return pts.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
	}

	/** Text that must fit a box, by characters at the drawing's type size. */
	const clip = (t: string, n: number) => (t.length > n ? t.slice(0, n - 1) + '…' : t);

	/** Whether a card's line is one the hovered or selected result is in. */
	const lineHolds = (e: { members: { from: string; to: string }[] }, id: string) => !!id && e.members.some((p) => p.from === id || p.to === id);

	/** A pointer position in the drawing's own coordinates. The screen matrix accounts for the letterboxing `preserveAspectRatio` adds when the canvas and the drawing differ in shape, which a proportional mapping does not. */
	function toDiagram(ev: { clientX: number; clientY: number }): { x: number; y: number } {
		const ctm = svgEl?.getScreenCTM();
		if (!svgEl || !ctm) return { x: 0, y: 0 };
		const p = new DOMPoint(ev.clientX, ev.clientY).matrixTransform(ctm.inverse());
		return { x: p.x, y: p.y };
	}

	function down(ev: PointerEvent, id?: string) {
		const p = toDiagram(ev);
		dragging = { kind: id && laidMode === 'dots' ? 'node' : 'pan', id, x: p.x, y: p.y };
		(ev.currentTarget as Element).setPointerCapture?.(ev.pointerId);
	}
	function move(ev: PointerEvent) {
		if (!dragging || !laid) return;
		const p = toDiagram(ev);
		const dx = p.x - dragging.x;
		const dy = p.y - dragging.y;
		if (dragging.kind === 'pan') {
			// shifting the view by the pointer's travel puts the anchor back under the pointer, so the anchor itself stays put
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
	/** Zoom about the pointer, so the thing being looked at stays under it. */
	function wheel(ev: WheelEvent) {
		ev.preventDefault();
		if (!drawing) return;
		const before = toDiagram(ev);
		const next = Math.min(6, Math.max(0.2, scale * Math.exp(-ev.deltaY / 400)));
		const f = scale / next;
		tx = before.x - (before.x - tx) * f;
		ty = before.y - (before.y - ty) * f;
		scale = next;
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
	const viewBox = $derived(drawing ? `${tx} ${ty} ${drawing.width / scale} ${drawing.height / scale}` : '0 0 100 100');
	const stateOk = (id: string) => !stateFilter || m.nodes[id]?.state === stateFilter;
	const dimmed = (id: string) => (selected && !related.has(id) && id !== selected) || !stateOk(id);
	const modes: [Mode, string][] = [
		['dots', 'Dots'],
		['box', 'Box'],
		['sections', 'Sections'],
		['reading', 'Reading Order']
	];
</script>

<main class="page graph">
	<header class="head">
		<h1>Graph</h1>
		<div class="toggle" role="group" aria-label="Drawing">
			{#each modes as [id, label] (id)}
				<button class:on={mode === id} aria-pressed={mode === id} onclick={() => (mode = id)} data-testid="layout-{id}">{label}</button>
			{/each}
		</div>
		<button class="as-link" onclick={reset}>reset view</button>
	</header>

	{#if !m.masters.length}
		<NoDrafts what="results to draw" />
	{:else if error}
		<p class="problem">{error}</p>
	{:else if !drawing && laidMode !== 'reading'}
		<p class="faint">Laying out…</p>
	{:else}
		<p class="faint">
			{counts} · solid statement, dashed proof, dotted prose · {external === 'papers' ? 'a box is a cited paper, dash-dot a citation · ' : ''}{caption}{laidMode === 'reading' ? '' : ' · drag to pan, scroll to zoom'}, click to select, double-click to open
		</p>
		{#if laidMode === 'reading' && reading}
			<div class="canvas scrolls" data-testid="reading-canvas">
				<svg viewBox="0 0 {reading.width} {reading.height}" width="100%" height={reading.height} role="application" aria-label="dependency graph in reading order" preserveAspectRatio="xMidYMin meet">
					{#each reading.arcs as a, i (i)}
						<path d={a.d} class="edge edge-{a.kind}" class:lit={hover === a.from || hover === a.to || selected === a.from || selected === a.to} class:soft={(!!hover && a.from !== hover && a.to !== hover) || dimmed(a.from)} />
					{/each}
					{#each reading.rows as r (r.id)}
						{@const inScope = !scope || scope.has(r.id)}
						<g
							class="row"
							class:soft={!inScope || (r.kind === 'result' && dimmed(r.id))}
							onpointerenter={() => (hover = r.id)}
							onpointerleave={() => (hover = hover === r.id ? '' : hover)}
							onclick={() => (selected = r.kind === 'result' ? r.id : '')}
							ondblclick={() => (location.href = open(r.id))}
							role="button"
							tabindex="0"
							onkeydown={(e) => e.key === 'Enter' && (selected = r.id)}
							data-testid="grow-{r.id}"
						>
							<rect x={reading.gutter - 4} y={r.y - 15} width={reading.width - reading.gutter} height="19" rx="3" class="rowbg" class:on={hover === r.id || selected === r.id || related.has(r.id)} />
							{#if r.kind === 'section'}
								<text x={reading.gutter + 4 + r.depth * 11} y={r.y} class="row-section">{r.label}</text>
							{:else}
								<rect x={reading.gutter + 8 + r.depth * 11} y={r.y - 11} width="6" height="13" rx="2" class="chip fill-{r.color}" stroke-dasharray={r.external ? '2 1.5' : ''} />
								<text x={reading.gutter + 22 + r.depth * 11} y={r.y} class="row-result">{r.label}</text>
							{/if}
						</g>
					{/each}
				</svg>
			</div>
		{:else}
			<div class="canvas">
				<svg
					bind:this={svgEl}
					{viewBox}
					role="application"
					aria-label="dependency graph"
					class:layered={laidMode !== 'dots'}
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
					{#if laidMode === 'sections' && cards}
						{#each cards.edges as e, i (i)}
							<path
								d={path(e.points, e)}
								class="edge edge-{e.kind}"
								stroke-width={1 + Math.min(3, Math.log2(e.count + 1))}
								class:lit={lineHolds(e, hover) || lineHolds(e, selected)}
								class:dim={(!!selected && !lineHolds(e, selected) && !related.has(e.from)) || (!!hover && !lineHolds(e, hover))}
								marker-end="url(#arrow)"
							/>
						{/each}
						{#each cards.cards as c (c.id)}
							<g
								class="card"
								data-testid="gcard-{c.id}"
								onpointerdown={(e) => {
									e.stopPropagation();
									down(e);
								}}
								onclick={() => (selected = m.nodes[c.id] ? c.id : '')}
								ondblclick={() => m.nodes[c.id] && (location.href = open(c.id))}
								role="button"
								tabindex="0"
								onkeydown={(e) => e.key === 'Enter' && m.nodes[c.id] && (selected = c.id)}
							>
								<rect x={c.x} y={c.y} width={c.w} height={c.h} rx="6" class="card-box" class:selected={selected === c.id} />
								<text x={c.x + 8} y={c.y + 16} class="card-label">{c.label}</text>
								{#each c.rows as r (r.id)}
									<g
										class="crow"
										class:dim={dimmed(r.id) || (!!scope && !scope.has(r.id))}
										onpointerdown={(e) => {
											// the canvas captures the pointer to pan, which would make every click land on the canvas; capturing here keeps the click on the row and still pans
											e.stopPropagation();
											down(e);
										}}
										onpointerenter={() => (hover = r.id)}
										onpointerleave={() => (hover = hover === r.id ? '' : hover)}
										onclick={(e) => {
											e.stopPropagation();
											selected = r.id;
										}}
										ondblclick={(e) => {
											e.stopPropagation();
											location.href = open(r.id);
										}}
										role="button"
										tabindex="0"
										onkeydown={(e) => e.key === 'Enter' && (selected = r.id)}
										data-testid="grow-{r.id}"
									>
										<rect x={c.x + 4} y={c.y + r.dy - 11} width={c.w - 8} height="14" rx="2" class="rowbg" class:on={hover === r.id || selected === r.id || related.has(r.id)} />
										<rect x={c.x + 8} y={c.y + r.dy - 9} width="5" height="10" rx="1.5" class="chip fill-{r.color}" stroke-dasharray={r.external ? '2 1.5' : ''} />
										<text x={c.x + 18} y={c.y + r.dy} class="crow-label">{r.label}</text>
									</g>
								{/each}
							</g>
						{/each}
					{:else}
						{#each shownEdges as e, i (i)}
							<path
								d={path(e.points, e)}
								class="edge edge-{e.kind}"
								stroke-width={e.count && e.count > 1 ? 1.1 + Math.min(3, Math.log2(e.count)) : undefined}
								class:dim={selected && !related.has(e.from) && e.from !== selected}
								marker-end={laidMode === 'box' ? 'url(#arrow)' : undefined}
							/>
						{/each}
						{#each shown as n (n.id)}
							{@const p = at(n.id, n.x, n.y)}
							<g
								class="node"
								class:paper={n.style === 'paper'}
								class:selected={n.id === selected}
								class:hl={related.has(n.id)}
								class:dim={dimmed(n.id)}
								onpointerdown={(e) => {
									e.stopPropagation();
									down(e, n.id);
								}}
								onclick={() => (selected = n.id)}
								ondblclick={() => (location.href = open(n.id))}
								role="button"
								tabindex="0"
								onkeydown={(e) => e.key === 'Enter' && (selected = n.id)}
								data-testid="gnode-{n.id}"
							>
								{#if laidMode === 'dots' && n.style === 'paper'}
									<rect x={p.x - R * 1.4} y={p.y - R * 1.4} width={R * 2.8} height={R * 2.8} rx="2" class="paper-box" />
									<text x={p.x} y={p.y + R * 1.4 + 10} class="under">{n.label}</text>
								{:else if laidMode === 'dots'}
									<circle cx={p.x} cy={p.y} r={n.id === selected ? R * 1.7 : n.section ? R * 1.3 : R} class="taxon fill-{n.color}" style="--taxon-tone: {n.tone}" stroke-dasharray={n.external ? '3 2' : ''} />
									<text x={p.x} y={p.y + R + 10} class="under">{n.id}</text>
								{:else if n.style === 'paper'}
									<rect x={p.x} y={p.y} width={n.w} height={n.h} rx="2" class="paper-box" />
									<text x={p.x + 8} y={p.y + 21}><tspan class="taxon">paper</tspan> <tspan class="id">{n.label}</tspan></text>
								{:else}
									<rect x={p.x} y={p.y} width={n.w} height={n.h} rx={n.style === 'definition' ? 12 : n.style === 'remark' ? 0 : 4} class="taxon fill-{n.color}" style="--taxon-tone: {n.tone}" stroke-dasharray={n.external ? '4 2' : ''} />
									<text x={p.x + 8} y={p.y + 15}><tspan class="id">{n.id}</tspan> <tspan class="taxon">{n.taxon}</tspan></text>
									{#if n.note}<text x={p.x + 8} y={p.y + 27} class="note">{clip(n.note, 24)}</text>{/if}
								{/if}
							</g>
						{/each}
					{/if}
				</svg>
			</div>
		{/if}
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
		<label>cited results<select bind:value={external} data-testid="filter-cited"><option value="reached">used here</option><option value="all">all</option><option value="papers">as papers</option><option value="none">none</option></select></label>
	</div>
</PagePanel>

{#if paper}
	<PageRail>
		<RailList label="selected paper">
			<p class="sel"><a href={digestUrl(paper.citekey)}>{bibText(paper.bib.title) || paper.citekey}</a></p>
			<p class="faint">{bibText(paper.bib.author)}{paper.bib.year ? ` · ${paper.bib.year}` : ''}</p>
			<p><WorkLinks ref={paper} /></p>
			<p class="faint">{related.size} {related.size === 1 ? 'result here uses' : 'results here use'} it{paper.digest ? ` · digest of ${paper.digest.nodes.length}` : ' · no digest'}</p>
			<p><button class="as-link" onclick={() => (selected = '')}>clear</button></p>
		</RailList>
	</PageRail>
{:else if node}
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
	.canvas.scrolls {
		overflow: auto;
	}
	.canvas.scrolls svg {
		height: auto;
		cursor: default;
	}
	svg {
		width: 100%;
		height: 100%;
		touch-action: none;
		cursor: grab;
	}
	.card-box {
		fill: color-mix(in srgb, var(--link) 5%, var(--sheet));
		stroke: var(--rule);
	}
	.card-box.selected {
		stroke: var(--link);
		stroke-width: 2;
	}
	.card-label,
	.row-section {
		font-family: var(--sans);
		font-size: 11px;
		font-weight: 600;
		fill: var(--ink-soft);
		pointer-events: none;
	}
	.crow-label,
	.row-result {
		font-family: var(--sans);
		font-size: 11px;
		fill: var(--ink);
		pointer-events: none;
	}
	.crow-label {
		font-size: 10px;
	}
	.crow,
	.row {
		cursor: pointer;
	}
	.rowbg {
		fill: transparent;
	}
	.rowbg.on {
		fill: var(--link-wash);
	}
	.chip {
		stroke: var(--rule-strong);
		stroke-width: 0.8;
	}
	.edge {
		fill: none;
		stroke: var(--rule-strong);
		stroke-width: 1.1;
	}
	.edge-proof {
		stroke-dasharray: 5 3;
	}
	.edge-cites {
		stroke-dasharray: 6 2 1 2;
	}
	.edge-prose {
		stroke-dasharray: 1.5 3;
	}
	.edge.lit {
		stroke: var(--link);
	}
	.paper-box {
		fill: var(--leaf);
		stroke: var(--ink-soft);
		stroke-width: 1.4;
	}
	.node.selected .paper-box {
		stroke: var(--link);
		stroke-width: 2.5;
	}
	.node.hl .paper-box {
		stroke: var(--link);
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
	.node .taxon,
	.node text.note {
		fill: var(--ink-faint);
	}
	.node text.note {
		font-size: 9px;
	}
	/* The taxon is the fill and the state is the ring: what a node IS does not change while you work, and how it
	   stands does, so the slower fact gets the larger area. `fill-*` still sets the stroke, which is why both apply. */
	.node circle.taxon,
	.node rect.taxon {
		fill: color-mix(in srgb, var(--taxon-tone) 30%, var(--sheet));
		stroke: var(--taxon-tone);
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
	/* a row of text is unreadable at the dimming a shape tolerates, so what is not in play is only half faded */
	.soft {
		opacity: 0.55;
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
