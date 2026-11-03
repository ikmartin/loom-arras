<script lang="ts">
	// The head of each of Review's sections: its name alone, since a section is about the whole quilt and the column already names the quilt; a page about one document says which inside itself.
	import type { Snippet } from 'svelte';

	let { title, aside }: { title: string; aside?: Snippet } = $props();
</script>

<header class="heading"><h1>{title}</h1>{#if aside}{@render aside()}{/if}</header>

<style>
	.heading {
		display: flex;
		align-items: baseline;
		gap: var(--gap-tight);
		padding: 0 2px 16px;
		flex-wrap: wrap;
	}
	.heading h1 {
		font: 400 24px/1.2 Georgia, serif;
		margin: 0;
	}
</style>
