<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import { nodeBadge, reviewFacts, stateBadge } from '$lib/badges';
	import { digestUrl, keyFromParam, masterUrl, nodeUrl, tagUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	const key = $derived(keyFromParam(page.params.key ?? ''));
	const node = $derived(m.nodes[key]);
	const stmt = $derived(m.keys[key]);
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
	const dependents = $derived(m.edges.filter((e) => e.to === key || (node?.proofs ?? []).includes(e.to)));
	const diagnostics = $derived(m.diagnostics.filter((d) => d.keys.includes(key)));
	const annotations = $derived(Object.values(m.annotations).filter((a) => a.target.key === key || (node?.proofs ?? []).includes(a.target.key)));
	const detached = $derived(annotations.filter((a) => a.detached && !a.discarded));
	const threads = $derived(Object.values(m.threads).filter((t) => t.targets.includes(key)));
	const closure = $derived(stmt?.closure.filter((k) => k !== key) ?? []);
</script>

<main class="page">
	{#if !node}
		<h1>Unknown key</h1>
		<p>The manifest has no node <code>{key}</code>.</p>
	{:else}
		<p class="meta">
			<span class="taxon">{node.taxon}</span>
			<code title={node.aliases.join(', ')}>{node.id}</code>
			{#if number}<span>· {number}</span>{:else}<span class="muted">· not yet compiled</span>{/if}
			{#if node.created}<span class="muted">· {node.created}</span>{/if}
			{#if node.author?.length}<span class="muted">· {node.author.join(', ')}</span>{/if}
			{#each node.tags as t (t)}<a class="tag" href={tagUrl(t)}>#{t}</a>{/each}
			{#if node.external && node.digest}<span>· from <a href={digestUrl(node.digest)}>{node.digest}</a>{node.locator ? `, ${node.locator}` : ''}</span>{/if}
		</p>
		<h1>{node.title ?? node.id}</h1>
		<p><Badge parts={nodeBadge(m, node)} facts={reviewFacts(stmt)} /></p>

		<Fragment path={node.fragment} macroSet={node.digest ?? ''} />

		{#each node.proofs as pk (pk)}
			<p class="proof-badge"><code>{pk}</code> <Badge parts={stateBadge(m, m.keys[pk])} facts={reviewFacts(m.keys[pk])} /></p>
		{/each}

		<h2>Context</h2>
		{#if node.reached_by.length}
			<ul>
				{#each node.reached_by as mp (mp)}
					<li>
						in <a href={masterUrl(mp)}>{mp}</a>:
						{#each chain(mp) as ck, i (ck)}
							{#if i > 0}›{/if}
							<a href={nodeUrl(ck)}>{m.nodes[ck]?.title ?? ck}</a>
						{/each}
					</li>
				{/each}
			</ul>
		{:else}
			<p class="muted">loose: no master reaches this node</p>
		{/if}

		<h2>Dependencies</h2>
		{#if deps.length}
			<ul>
				{#each deps as e, i (i)}
					<li>{e.kind}-edge <a href={nodeUrl(e.to)}>{e.to}</a> {m.nodes[e.to]?.title ? `(${m.nodes[e.to].taxon} ${m.nodes[e.to].title})` : ''} <span class="muted">via {e.via}</span></li>
				{/each}
			</ul>
		{:else}
			<p class="muted">None.</p>
		{/if}
		{#if closure.length}
			<p class="muted">Read first: {#each closure as ck, i (ck)}{#if i > 0}, {/if}<a href={nodeUrl(ck)}>{ck}</a>{/each}</p>
		{/if}

		<h2>Dependents</h2>
		{#if dependents.length}
			<ul>
				{#each dependents as e, i (i)}
					<li><a href={nodeUrl(e.from)}>{e.from}</a> <span class="muted">{e.kind} via {e.via}</span></li>
				{/each}
			</ul>
		{:else}
			<p class="muted">None.</p>
		{/if}

		{#if node.children.length}
			<h2>Contents</h2>
			<ul>
				{#each node.children as ck (ck)}
					<li><a href={nodeUrl(ck)}>{m.nodes[ck]?.taxon ?? ''} {m.nodes[ck]?.title ?? ck}</a></li>
				{/each}
			</ul>
		{/if}

		{#if threads.length}
			<h2>Discussions</h2>
			<ul>{#each threads as t (t.id)}<li><a href={'/thread/' + encodeURIComponent(t.id)}>{t.title}</a></li>{/each}</ul>
		{/if}

		{#if detached.length}
			<h2>Detached annotations</h2>
			<ul>{#each detached as a (a.id)}<li><em>{a.quote}</em>: {@html a.body_html}</li>{/each}</ul>
		{/if}

		<h2>Diagnostics</h2>
		<Diagnostics items={diagnostics} />
	{/if}
</main>

<style>
	.meta {
		color: var(--muted);
		font-size: 0.9rem;
	}
	.meta .taxon {
		font-weight: 600;
		color: var(--fg);
	}
	.tag {
		margin-left: 0.5rem;
	}
	.proof-badge {
		font-size: 0.9rem;
	}
</style>
