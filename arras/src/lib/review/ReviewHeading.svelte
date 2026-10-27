<script lang="ts">
	// The head of each of Review's sections: the section's name, and the corpus it is about.
	import { store } from '$lib/manifest/client.svelte';

	let { title }: { title: string } = $props();
	const m = $derived(store.manifest);
</script>

<header class="heading"><h1>{title}</h1><span>{m?.corpus.root_label || m?.corpus.name}</span></header>

<style>
	.heading {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 20px;
		padding: 0 2px 16px;
		flex-wrap: wrap;
	}
	.heading h1 {
		font: 400 24px/1.2 Georgia, serif;
		margin: 0;
	}
	.heading span {
		font-size: 12px;
		color: var(--ink-soft);
	}
</style>
