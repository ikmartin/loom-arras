<script lang="ts">
	// A cited work's outward links (book 10.2.3): its identifiers at the services that resolve them, and the fetched PDF when there is one. Each opens in a new tab, since each leaves the corpus.
	import type { Reference } from '$lib/manifest/types';
	import { resolve, workLinks } from '$lib/works';

	let { ref }: { ref: Reference } = $props();
	const links = $derived(workLinks(ref));
	// a lookup's proposal, shown only while the entry states no identifier of its own, and marked as unconfirmed
	const candidate = $derived(links.some((l) => l.label !== 'PDF' && l.label !== 'link') ? undefined : ref.candidates?.[0]);
	const candidateLink = $derived(candidate ? resolve(candidate.id) : null);
</script>

{#if links.length || candidateLink}
	<span class="work-links" data-testid="work-links-{ref.citekey}">
		{#each links as l (l.href)}
			<a href={l.href} title={l.id} target="_blank" rel="noopener noreferrer" class:pdf={l.label === 'PDF'}>{l.label}</a>
		{/each}
		{#if candidate && candidateLink}
			<a href={candidateLink.href} class="candidate" target="_blank" rel="noopener noreferrer" title="unconfirmed: a lookup found {candidate.id} ({candidate.strength} match, {candidate.source}), “{candidate.title}”. It becomes this work's identifier when the bibliography entry states it." data-testid="candidate-{ref.citekey}">{candidateLink.label}?</a>
		{/if}
	</span>
{/if}

<style>
	.work-links {
		display: inline-flex;
		flex-wrap: wrap;
		gap: var(--gap-hair);
		font-family: var(--sans);
		font-size: 10px;
		vertical-align: baseline;
	}
	a {
		padding: 0 5px;
		line-height: 15px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		background: var(--sheet);
		white-space: nowrap;
	}
	a:hover {
		text-decoration: none;
		border-color: var(--link);
	}
	a.candidate {
		border-style: dashed;
		color: var(--ink-soft);
	}
	a.pdf {
		background: var(--link-wash);
		border-color: transparent;
	}
</style>
