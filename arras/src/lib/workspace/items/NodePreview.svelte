<script lang="ts">
	// A node, rendered small for a hover card (plan 0.13.3 H1–H3): its label, number, id and state, and its statement typeset — proofs hidden, the text clamped by a fade rather than cut. A section says how many entries it holds and no more: its fragment is the whole section, too much to fetch and typeset for a glance.
	import { tick } from 'svelte';
	import { displayNode } from '$lib/nodes/display';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { wire } from '$lib/fragments/mount';
	import { typeset } from '$lib/math/mathjax';
	import { nodeBadge } from '$lib/badges';
	import Badge from '$lib/components/Badge.svelte';
	import type { Item } from '../item';

	let { item, onresize = () => {}, master = '', persistent = false }: { item: Item; onresize?: () => void; master?: string; persistent?: boolean } = $props();

	const m = $derived(store.manifest!);
	const node = $derived(m.nodes[item.id]);
	const identity = $derived(displayNode(m, item.id, master));
	let html = $state('');
	let body: HTMLElement | undefined = $state();

	$effect(() => {
		const current = node;
		const manifest = m;
		const hash = store.hash;
		void master;
		html = '';
		let gone = false;
		void (async () => {
			if (!current || current.kind === 'section') return;
			const text = await fetchFragment(current.fragment, hash).catch(() => '<p>Statement preview unavailable.</p>');
			if (gone) return;
			html = text;
			await tick();
			if (!body || gone) return;
			wire(body, manifest, () => {});
			const sets = manifest.macros.sets ?? {};
			await typeset(body, manifest.macros.default ?? [], current.digest ? (sets[current.digest] ?? []) : []);
			if (!gone) onresize();
		})();
		return () => {
			gone = true;
		};
	});
</script>

{#if node}
	<p class="head">
		<span class="label">{identity.name}</span>
		{#if identity.context}<span class="title">{identity.context}</span>{/if}
		<span class="id">{node.id}</span>
	</p>
	<p class="state"><Badge parts={nodeBadge(m, node)} />{#if node.external && node.digest}<span class="from">from {node.digest}{node.locator ? ', ' + node.locator : ''}</span>{/if}</p>
	{#if node.kind === 'section'}
		{#if node.children.length}<p class="more">{node.children.length} {node.children.length === 1 ? 'entry' : 'entries'} in this section</p>{/if}
	{:else}
		<div class="body fragment" class:persistent bind:this={body}>{@html html}</div>
	{/if}
{/if}

<style>
	p {
		margin: 0;
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 var(--gap-tight);
	}
	.label {
		font-weight: 500;
		color: var(--ink);
	}
	.title {
		font-family: var(--body-face);
		font-size: 13px;
		color: var(--ink);
	}
	.id {
		margin-left: auto;
		font-family: var(--mono);
		font-size: 9px;
		color: var(--link);
	}
	.state {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--gap-tight);
		margin: var(--gap-hair) 0;
	}
	.from,
	.more {
		color: var(--ink-faint);
		font-size: 10px;
	}
	/* Clamped by height with a fade rather than by truncating the text, which could split a formula; the fade reads as continuing rather than ending. */
	.body {
		max-height: 12rem;
		overflow: hidden;
		-webkit-mask-image: linear-gradient(to bottom, #000 9rem, transparent);
		mask-image: linear-gradient(to bottom, #000 9rem, transparent);
		font-size: 12.5px;
		text-align: left;
	}
	.body.persistent { max-height: 28rem; overflow: auto; -webkit-mask-image: none; mask-image: none; }
	.body :global(p) { text-align: left; }
	.body :global(.env) {
		margin: 0;
	}
	/* the card's own header already names the result, and a proof is not what a glance is for */
	.body :global(details.env-proof),
	.body :global(.node-margin),
	.body :global(a.heading-link),
	.body :global(.env > .env-label) {
		display: none !important;
	}
	.body :global(.math.display) {
		background: none;
	}
</style>
