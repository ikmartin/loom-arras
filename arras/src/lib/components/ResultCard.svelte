<script lang="ts">
	// One result of a cited work on its Info (plan 0.24.3): its number and name, its state, the page it is printed on, the statement itself, and which of the person's keys use it. The number goes to the result's own page, where what is said about it is; the page opens the paper there.
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import Statement from '$lib/math/Statement.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import type { WorkResult } from '$lib/library';
	import { isAgentDocument } from '$lib/manifest/documents';
	import { keyUrl, nodeUrl } from '$lib/nav';
	import { keyName } from '$lib/workspace/names';
	import Locator from './Locator.svelte';

	let { citekey, result }: { citekey: string; result: WorkResult } = $props();

	const m = $derived(store.manifest!);
	const id = $derived(result.id);
	const node = $derived(m.nodes[id]);
	const record = $derived(m.references[citekey]?.results?.[id]);
	const locator = $derived((node?.locator ?? '').replace(/~/g, ' '));
	const named = $derived(locator.split(',')[0].trim() || record?.local || id);
	// the page part of the locator, else the page a proposal names; Locator makes it a link where the paper can be opened there
	const page = $derived(locator.includes(',') ? locator.slice(locator.indexOf(',') + 1).trim() : record?.page ? `p. ${record.page}` : '');
	// the person's keys that cite it, once each: not an agent document's, and not another result of a digest, which is the paper citing itself
	const users = $derived(
		[...new Set(m.edges.filter((e) => e.to === id).map((e) => e.from))].filter((k) => {
			const n = m.nodes[k.split('/')[0]];
			return !n?.derived_of && !n?.external && !isAgentDocument(m.masters.find((x) => x.path === k));
		})
	);
</script>

<article class="result" data-testid="result-card" data-result={id}>
	<header>
		<a class="num" href={nodeUrl(id)} data-testid="result-name">{named}</a>
		{#if node?.title}<span class="name">(<Tex text={node.title} />)</span>{/if}
		<span class="badge {result.state}" data-testid="result-state">{result.state}</span>
		{#if page}<span class="where"><Locator {id} locator={page} /></span>{/if}
	</header>
	<div class="stmt">
		{#if node?.fragment}
			{#key id}<Fragment path={node.fragment} macroSet={citekey} anchor="" standalone />{/key}
		{:else if record?.statement}
			<Statement text={record.statement} />
		{/if}
	</div>
	{#if users.length}
		<p class="used" data-testid="result-used">used by {#each users as k, i (k)}{i ? ', ' : ''}<a href={keyUrl(m, k)}>{keyName(m, k)}</a>{/each}</p>
	{/if}
</article>

<style>
	.result {
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		background: var(--sheet);
		padding: 10px 14px;
		margin: 0 0 8px;
	}
	header {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-family: var(--sans);
		font-size: 12px;
	}
	.num {
		font-family: var(--serif);
		font-size: 14px;
		font-weight: 600;
		color: var(--ink);
		text-decoration: none;
	}
	.num:hover {
		color: var(--link);
	}
	.name {
		font-family: var(--serif);
		font-size: 14px;
		font-style: italic;
		color: var(--ink-soft);
	}
	.badge {
		font-size: 10.5px;
		border-radius: var(--rad-pill);
		padding: 1px 7px;
		background: var(--leaf);
		color: var(--ink-soft);
	}
	.badge.verified {
		background: var(--state-accepted-wash);
		color: var(--state-accepted);
	}
	.badge.proposed {
		background: var(--state-stale-wash);
		color: var(--state-stale);
	}
	.where {
		margin-left: auto;
		color: var(--ink-faint);
	}
	.stmt {
		margin: 6px 0 0;
	}
	/* the card's head already names the result and its page, so the environment's own label is not said twice; the reading formats set it inline, hence the weight */
	.stmt :global(.env > .env-label) {
		display: none !important;
	}
	.stmt :global(p:first-child) {
		margin-top: 0;
	}
	.stmt :global(p:last-child) {
		margin-bottom: 0;
	}
	.used {
		margin: 6px 0 0;
		font-family: var(--sans);
		font-size: 11.5px;
		color: var(--ink-faint);
	}
</style>
