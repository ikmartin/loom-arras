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
	import { nodeBadge, reviewFacts, stateBadge } from '$lib/badges';
	import { digestUrl, keyFromParam, keyUrl, masterUrl, nodeUrl, tagUrl, threadUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
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
	const deps = $derived(m.edges.filter((e) => e.from === key || node?.proofs.includes(e.from)));
	const usedBy = $derived(m.edges.filter((e) => e.to === key || (node?.proofs ?? []).includes(e.to)));
	const diagnostics = $derived(m.diagnostics.filter((d) => d.keys.includes(key)));
	const annotations = $derived(Object.values(m.annotations).filter((a) => a.target.key === key || (node?.proofs ?? []).includes(a.target.key)));
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
			<h1>{node.title ?? node.id}{#if number}<span class="num">{number}</span>{/if}</h1>
			<p class="meta">
				<span class="taxon">{node.taxon}</span>
				<IdChip id={node.id} aliases={node.aliases} />
				<Badge parts={nodeBadge(m, node)} facts={reviewFacts(stmt)} />
				{#if !number}<span class="muted">not yet compiled</span>{/if}
				{#each node.tags as t (t)}<a class="tag" href={tagUrl(t)}>#{t}</a>{/each}
				{#if node.external && node.digest}<span class="muted">from <a href={digestUrl(node.digest)}>{node.digest}</a>{node.locator ? `, ${node.locator}` : ''}</span>{/if}
			</p>
		</header>

		<Fragment path={node.fragment} macroSet={node.digest ?? ''} />

		{#if node.proofs.length}
			<div class="proof-states">
				{#each node.proofs as pk (pk)}
					<p><code>{pk}</code> <Badge parts={stateBadge(m, m.keys[pk])} facts={reviewFacts(m.keys[pk])} /></p>
				{/each}
			</div>
		{/if}

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
			<RailList label="in" empty="loose: no document reaches this node" />
		{/each}

		<RailList label="depends on" empty={deps.length ? '' : 'nothing'}>
			{#if deps.length}
				<ul class="plain">
					{#each deps as e, i (i)}
						<li><a href={keyUrl(m, e.to)}>{label(e.to)}</a> <span class="faint">{e.kind}</span></li>
					{/each}
				</ul>
				{#if closure.length}<p class="faint">read first: {closure.length} more</p>{/if}
			{/if}
		</RailList>

		<RailList label="used by" empty={usedBy.length ? '' : 'nothing'}>
			{#if usedBy.length}
				<ul class="plain">
					{#each usedBy as e, i (i)}
						<li><a href={keyUrl(m, e.from)}>{label(e.from)}</a> <span class="faint">{e.kind}</span></li>
					{/each}
				</ul>
			{/if}
		</RailList>

		{#each relations as [kind, items] (kind)}
			<RailList label={kind === 'see' ? 'see also' : kind}>
				<ul class="plain">
					{#each items as k (k)}
						<li><a href={keyUrl(m, k)}>{label(k)}</a></li>
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
