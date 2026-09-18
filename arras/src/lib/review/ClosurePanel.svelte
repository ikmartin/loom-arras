<script lang="ts">
	// The closure of a result, stacked in dependency order with the result last (plan 0.11 Part D).
	//
	// A panel and not a route: a closure is a way of looking at a node, not a place to go, and the graph that answers the opposite question sits beside it on the same page.
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { nodeUrl } from '$lib/nav';
	import { stack } from './closure';

	let { center }: { center: string } = $props();

	const m = $derived(store.manifest!);
	let depth = $state(1);
	const keys = $derived(stack(m, center, depth));
</script>

<section class="closure" data-testid="closure-panel">
	<header>
		<span class="label">rests on</span>
		<span class="depths">
			{#each [1, 2] as d (d)}
				<button class:on={depth === d} onclick={() => (depth = d)} data-testid="closure-depth-{d}">depth {d}</button>
			{/each}
		</span>
	</header>
	{#if keys.length <= 1}
		<p class="faint">This result rests on nothing else in the corpus.</p>
	{:else}
		<ol class="stack">
			{#each keys as k (k)}
				{@const node = m.nodes[m.keys[k]?.node ?? k]}
				<li class:centre={k === center} data-key={k}>
					<p class="who">
						<a href={nodeUrl(m.keys[k]?.node ?? k)}>{node?.taxon ?? ''} {node?.title ?? k}</a>
						<code>{k}</code>
					</p>
					{#if node?.fragment}<Fragment path={node.fragment} macroSet={node.digest ?? ''} />{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>

<style>
	.closure {
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		padding: var(--gap);
		background: var(--sheet);
	}
	.closure header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--gap);
		margin-bottom: var(--gap-tight);
	}
	.label {
		font-family: var(--sans);
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
	}
	.depths button {
		background: none;
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 0 0.4em;
		margin-left: 0.3em;
		font-family: var(--sans);
		font-size: 0.72em;
		color: var(--ink-soft);
		cursor: pointer;
	}
	.depths button.on {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
	ol.stack {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	ol.stack > li + li {
		margin-top: var(--gap);
		border-top: 1px solid var(--rule);
		padding-top: var(--gap);
	}
	/* The result being read is the point of the stack, and everything above it is what it stands on. */
	ol.stack > li.centre {
		border-top-width: 2px;
		border-top-color: var(--rule-strong);
	}
	.who {
		display: flex;
		gap: var(--gap);
		align-items: baseline;
		justify-content: space-between;
		margin: 0 0 var(--gap-tight);
		font-size: 0.8em;
		color: var(--ink-faint);
	}
</style>
