<script lang="ts">
	// Fills the shell's right rail from a page. The content is a snippet so the page keeps ownership of it, and it is cleared when the page leaves.
	import type { Snippet } from 'svelte';
	import { rail } from './rail.svelte';

	let { children }: { children: Snippet } = $props();

	$effect(() => {
		rail.snippet = children;
		return () => {
			rail.snippet = null;
		};
	});
</script>
