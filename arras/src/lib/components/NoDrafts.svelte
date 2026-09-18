<script lang="ts">
	// What a view that is about nodes shows when nothing is being worked on (book 15.3.1).
	// The advice on how to start one is the publisher's, and arrives as a diagnostic with its own commands; this says only what is true of the corpus. The landmarks are still worth naming: a reader who arrives at an empty graph should be told where the mathematics is.
	import { store } from '$lib/manifest/client.svelte';
	import { canonUrl } from '$lib/nav';
	import { route } from '$lib/paths';

	let { what = 'results' }: { what?: string } = $props();
	const m = $derived(store.manifest);
	const landmarks = $derived(m?.canon?.length ? [...m.canon].reverse() : []);
</script>

<div class="empty" data-testid="no-drafts">
	<p class="head">Nothing is being worked on.</p>
	<p>
		The working drafts hold no document, so there are no {what}.
		{#if landmarks.length}
			The corpus's landmarks are still here: <a href={canonUrl(landmarks[0].path)}>{landmarks[0].title || landmarks[0].stem}</a
			>{#if landmarks.length > 1}, and {landmarks.length - 1} older{/if}.
		{/if}
		<a href={route('/problems')}>Problems</a> says how to start one.
	</p>
</div>

<style>
	.empty {
		max-width: var(--measure);
		font-size: 12px;
		line-height: 1.7;
		color: var(--ink-soft);
		padding: var(--gap-wide);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		background: var(--sheet);
	}
	.head {
		font-family: var(--sans);
		font-weight: 600;
		color: var(--ink);
		margin: 0 0 var(--gap-tight);
	}
	p {
		margin: 0;
	}
</style>
