<script lang="ts">
	// The node page (book 15.3.2): header, statement, each proof as its own block, and the context in the shell's right rail.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import IdChip from '$lib/components/IdChip.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import AnnotationPanel from '$lib/components/AnnotationPanel.svelte';
	import RailList from '$lib/components/RailList.svelte';
	import PageRail from '$lib/shell/PageRail.svelte';
	import LocalGraphPanel from '$lib/graph/LocalGraphPanel.svelte';
	import Locator from '$lib/components/Locator.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import SourceToggle from '$lib/components/SourceToggle.svelte';
	import ClosurePanel from '$lib/review/ClosurePanel.svelte';
	import { onAny } from '$lib/annotations';
	import Composer from '$lib/review/Composer.svelte';
	import ReferenceNotes from '$lib/review/ReferenceNotes.svelte';
	import { nodeBadge, reviewFacts, stateBadge, versionLabel } from '$lib/badges';
	import { anchorId, digestUrl, keyFromParam, keyUrl, masterUrl, nodeUrl, tagUrl, threadUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	let verbatim = $state(false);
	let restsOpen = $state(false);
	const key = $derived(keyFromParam(page.params.key ?? ''));
	const node = $derived(m.nodes[key]);
	const stmt = $derived(m.keys[key]);
	// A key with no node of its own — an unlabelled proof — belongs to the node that owns it, so the page points at it rather than reporting an unknown key.
	const owner = $derived(!node && stmt?.node && m.nodes[stmt.node] ? stmt.node : '');
	const defaultMaster = $derived(m.masters.find((x) => x.default)?.path);
	const number = $derived(node && defaultMaster ? node.numbers[defaultMaster]?.number : undefined);

	function chain(masterPath: string): string[] {
		const out: string[] = [];
		let cur = node?.parent[masterPath];
		let guard = 0;
		while (cur && guard++ < 20) {
			out.unshift(cur);
			cur = m.nodes[cur]?.parent[masterPath];
		}
		return out;
	}
	// One line per node, not one per edge: a statement and its two proofs all using the same lemma is one dependency, and listing it three times said nothing three times.
	function collapse(edges: { from: string; to: string; kind: string }[], side: 'to' | 'from') {
		const out = new Map<string, Set<string>>();
		for (const e of edges) {
			const other = e[side];
			(out.get(other) ?? out.set(other, new Set()).get(other)!).add(e.kind);
		}
		return [...out.entries()].map(([k, kinds]) => ({ key: k, kinds: [...kinds].sort() }));
	}
	const deps = $derived(collapse(m.edges.filter((e) => e.from === key || node?.proofs.includes(e.from)), 'to'));
	const usedBy = $derived(collapse(m.edges.filter((e) => e.to === key || (node?.proofs ?? []).includes(e.to)), 'from'));
	const diagnostics = $derived(m.diagnostics.filter((d) => d.keys.includes(key)));
	const missingProof = $derived(diagnostics.some((d) => d.code === 'loom:missing-proof'));
	const annotations = $derived(onAny(m, [key, ...(node?.proofs ?? [])]));
	const detached = $derived(annotations.filter((a) => a.detached && !a.discarded));
	const threads = $derived(Object.values(m.threads).filter((t) => t.targets.includes(key) && !t.discarded));
	const closure = $derived(stmt?.closure.filter((k) => k !== key) ?? []);
	// Both directions of every declared relation, grouped by kind; an unknown kind renders as a labelled link list like any other.
	const relations = $derived.by(() => {
		const out = new Map<string, string[]>();
		for (const r of m.relations ?? []) {
			const other = r.from === key ? r.to : r.to === key ? r.from : '';
			if (!other) continue;
			const list = out.get(r.kind) ?? [];
			if (!list.includes(other)) list.push(other);
			out.set(r.kind, list);
		}
		return [...out.entries()];
	});
	const label = (k: string) => {
		const n = m.nodes[k];
		if (!n) return k;
		return `${n.taxon}${n.title ? ' · ' + n.title : ''}`;
	};
</script>

<main class="page">
	{#if owner}
		<h1>{m.nodes[owner].title ?? owner}</h1>
		<p class="muted"><code>{key}</code> has no page of its own. It is part of <a href={keyUrl(m, key)}>{owner}</a>.</p>
	{:else if !node}
		<h1>Unknown key</h1>
		<p class="muted">The manifest has no node <code>{key}</code>.</p>
	{:else}
		<header class="node-head">
			<h1><Tex text={node.title ?? node.id} />{#if number}<span class="num">{number}</span>{/if}</h1>
			<p class="meta">
				<span class="taxon">{node.taxon}</span>
				<IdChip id={node.id} aliases={node.aliases} />
				<Badge parts={nodeBadge(m, node)} facts={reviewFacts(stmt)} />
				{#if versionLabel(stmt)}<span class="version" data-testid="version">{versionLabel(stmt)}</span>{/if}
				{#if !number && m.publishes.documents}<span class="muted">not yet numbered</span>{/if}
				{#each node.tags as t (t)}<a class="tag" href={tagUrl(t)}>#{t}</a>{/each}
				{#if node.external && node.digest}<span class="muted">from <a href={digestUrl(node.digest)}>{node.digest}</a>{#if node.locator}, <Locator ref={m.references[node.digest]} locator={node.locator} />{/if}</span>{/if}
			</p>
		</header>
		{#if missingProof}<p class="muted" data-testid="missing-proof">No proof is attached. <a href={`/review?show=missing-proof#review-${anchorId(key)}`}>See this block in Review</a>.</p>{/if}

		{#if node.conflict?.length}
			<p class="conflicted" data-testid="conflicted">
				Defined in two files: {#each node.conflict as f, i (f)}{#if i}{' and '}{/if}<code>{f}</code>{/each}. It has no
				text until one definition moves or is forked — see <a href="/problems?code=duplicate-id">problems</a>.
			</p>
		{:else}
			<!-- The toggle is the node's own text before macro expansion, fetched only when a reader asks; a corpus that publishes no source shows no control (plan 0.11 Part E). -->
			<div class="verbatim-head"><SourceToggle sourceKey={key} bind:open={verbatim} /></div>
			{#if !verbatim}
				<Fragment path={node.fragment} macroSet={node.digest ?? ''} />
			{/if}
		{/if}

		{#if node.proofs.length}
			<div class="proof-states">
				{#each node.proofs as pk (pk)}
					<p>
						<code>{pk}</code>
						<Badge parts={stateBadge(m, m.keys[pk])} facts={reviewFacts(m.keys[pk])} />
						{#if versionLabel(m.keys[pk])}<span class="version">{versionLabel(m.keys[pk])}</span>{/if}
					</p>
				{/each}
			</div>
		{/if}

		<Composer target={key} />
		<ReferenceNotes forKey={key} />

		<!-- The graph answers "what would this disturb"; the stack answers "what does this rest on". Neither is a route: a closure is a way of looking at a node, not a place to go. -->
		<details class="closure-open" data-testid="closure-open" bind:open={restsOpen}>
			<summary>What this rests on</summary>
			<!-- Built only once opened: the stack renders other results in full, and a closed panel that still mounted them would put six statements and their annotation marks on a page that shows one. -->
			{#if restsOpen}<ClosurePanel center={key} />{/if}
		</details>

		{#if node.children.length}
			<h2>On this page</h2>
			<ul class="plain">
				{#each node.children as ck (ck)}
					<li><a href={nodeUrl(ck)}>{m.nodes[ck]?.taxon ?? ''} {m.nodes[ck]?.title ?? ck}</a></li>
				{/each}
			</ul>
		{/if}

		<AnnotationPanel manifest={m} keys={[key, ...node.proofs]} />
	{/if}
</main>

{#if node}
	<PageRail>
		<RailList label="local graph">
			<!-- The graph could always be read and never entered; `hrefFor` is the whole of what it lacked (plan 0.11 Part D). -->
			<LocalGraphPanel center={key} hrefFor={(id) => nodeUrl(id)} />
		</RailList>

		{#each node.reached_by as mp (mp)}
			<RailList label={'in ' + mp}>
				<p class="crumb">
					<a href={masterUrl(mp)}>document</a>
					{#each chain(mp) as ck (ck)}
						<span class="sep">›</span><a href={nodeUrl(ck)}>{m.nodes[ck]?.title ?? ck}</a>
					{/each}
				</p>
			</RailList>
		{:else}
			{#if m.publishes.documents}<RailList label="in" empty="no document includes this node" />{/if}
		{/each}

		{#if deps.length}
			<RailList label="depends on">
				<ul class="plain">
					{#each deps as d (d.key)}
						<li><a href={keyUrl(m, d.key)}>{label(d.key)}</a> <span class="faint">{d.kinds.join(', ')}</span></li>
					{/each}
				</ul>
				{#if closure.length}<p class="faint">read first: {closure.length} more</p>{/if}
			</RailList>
		{:else}
			<RailList label="depends on" empty="nothing" />
		{/if}

		{#if usedBy.length}
			<RailList label="used by">
				<ul class="plain">
					{#each usedBy as d (d.key)}
						<li><a href={keyUrl(m, d.key)}>{label(d.key)}</a> <span class="faint">{d.kinds.join(', ')}</span></li>
					{/each}
				</ul>
			</RailList>
		{:else}
			<RailList label="used by" empty="nothing" />
		{/if}

		{#each relations as [kind, items] (kind)}
			<RailList label={kind === 'see' ? 'see also' : kind}>
				<ul class="plain" data-testid="relations-{kind}">
					{#each items as k (k)}
						<li>
							<a href={keyUrl(m, k)}>{label(k)}</a>
							<span class="faint">{m.nodes[k]?.reached_by?.length ? m.nodes[k].reached_by.join(', ') : m.publishes.documents ? 'no document' : ''}</span>
						</li>
					{/each}
				</ul>
			</RailList>
		{/each}

		{#if threads.length}
			<RailList label="discussions">
				<ul class="plain">
					{#each threads as t (t.id)}<li><a href={threadUrl(t.id)}>{t.title}</a></li>{/each}
				</ul>
			</RailList>
		{/if}

		{#if detached.length}
			<RailList label="detached comments">
				<ul class="plain">
					{#each detached as a (a.id)}<li><em>{a.quote}</em></li>{/each}
				</ul>
			</RailList>
		{/if}

		{#if diagnostics.length}
			<RailList label="diagnostics">
				<Diagnostics items={diagnostics} />
			</RailList>
		{/if}
	</PageRail>
{/if}

<style>
	.version {
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
	}
	.conflicted {
		max-width: var(--measure);
		font-size: 12px;
		line-height: 1.6;
		color: var(--ink-soft);
		padding: var(--gap-tight);
		border: 1px dashed var(--state-conflicted);
		border-radius: var(--rad-card);
		background: var(--state-conflicted-wash);
	}
	.node-head h1 {
		font-family: var(--body-face);
		font-size: 18px;
		font-weight: 500;
		display: flex;
		align-items: baseline;
		gap: var(--gap-tight);
	}
	.node-head .num {
		font-size: 13px;
		color: var(--ink-faint);
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--gap-tight);
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		margin: 0 0 var(--gap-wide);
	}
	.meta .taxon {
		color: var(--ink);
	}
	.proof-states {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		margin-top: var(--gap-wide);
	}
	.proof-states p {
		margin: var(--gap-hair) 0;
	}
	.crumb {
		font-size: 11px;
		margin: 0;
	}
	.crumb .sep {
		color: var(--ink-faint);
		margin: 0 3px;
	}
</style>
