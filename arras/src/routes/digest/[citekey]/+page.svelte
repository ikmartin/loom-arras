<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { keyUrl, nodeUrl } from '$lib/nav';
	import { reachedExternal } from '$lib/reached';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import { bibText } from '$lib/works';
	import Locator from '$lib/components/Locator.svelte';

	const m = $derived(store.manifest!);
	const citekey = $derived(decodeURIComponent(page.params.citekey ?? ''));
	const ref = $derived(m.references[citekey]);
	const citers = $derived((id: string) => [...new Set(m.edges.filter((e) => e.to === id).map((e) => e.from))]); // one entry per citing key, however many edges
	// A full extraction holds every theorem-like result of the cited paper, of which this corpus usually leans on a
	// handful. The rest is context worth having and not worth reading, so it folds.
	const reached = $derived(reachedExternal(m));
	const used = $derived((ref?.digest?.nodes ?? []).filter((id) => reached.has(id)));
	const rest = $derived((ref?.digest?.nodes ?? []).filter((id) => !reached.has(id)));
	let showAll = $state(false);
</script>

<main class="page">
	{#if !ref}
		<h1>Unknown reference</h1>
	{:else}
		<h1><Tex text={bibText(ref.bib.title) || citekey} /></h1>
		<p class="muted">
			<code>{citekey}</code>{ref.bib.author ? ` · ${bibText(ref.bib.author)}` : ''}{ref.bib.year ? ` · ${ref.bib.year}` : ''}
			<WorkLinks {ref} />
			{#if ref.digest}· digest from {ref.digest.source} ({ref.digest.method}){/if}
			{#if ref.version_mismatch}<span class="problem"> · version mismatch between the digest's source and the bibliography</span>{/if}
		</p>
		{#if ref.digest}
			<Fragment path={ref.digest.fragment} macroSet={citekey} />
			<h2>Results used here</h2>
			{#if used.length}
				<ul>
					{#each used as id (id)}
						<li><a href={nodeUrl(id)}>{id}</a> {#if m.nodes[id]?.locator}(<Locator {ref} locator={m.nodes[id].locator} />){/if}: {#each citers(id) as c, i (c)}{#if i}, {/if}<a href={keyUrl(m, c)}>{c}</a>{:else}<span class="muted">not cited</span>{/each}</li>
					{/each}
				</ul>
			{:else}
				<p class="muted">Nothing here depends on this reference yet.</p>
			{/if}
			{#if rest.length}
				<h2>
					<button class="fold" onclick={() => (showAll = !showAll)} aria-expanded={showAll} data-testid="digest-rest">
						{showAll ? '▾' : '▸'} {rest.length} further result{rest.length === 1 ? '' : 's'} nothing here uses
					</button>
				</h2>
				{#if showAll}
					<ul>
						{#each rest as id (id)}
							<li><a href={nodeUrl(id)}>{id}</a> {#if m.nodes[id]?.locator}(<Locator {ref} locator={m.nodes[id].locator} />){/if}</li>
						{/each}
					</ul>
				{/if}
			{/if}
		{:else}
			<p>No digest yet. Cited by: {#each ref.cited_by as c, i (c)}{#if i}, {/if}<a href={keyUrl(m, c)}>{c}</a>{:else}<span class="muted">nothing</span>{/each}</p>
		{/if}
	{/if}
</main>

<style>
	.fold {
		font: inherit;
		color: inherit;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
	}
</style>
