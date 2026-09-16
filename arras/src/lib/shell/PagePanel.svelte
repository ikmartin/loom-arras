<script lang="ts">
	// Fills the shell's left panel from a page, and clears it when the page leaves.
	import type { Snippet } from 'svelte';
	import { panel } from './panel.svelte';

	let { label = 'Filters', children }: { label?: string; children: Snippet } = $props();

	$effect(() => {
		panel.snippet = children;
		panel.label = label;
		return () => {
			panel.snippet = null;
			panel.label = '';
		};
	});
</script>
