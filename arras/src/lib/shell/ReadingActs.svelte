<script lang="ts">
	// Fills the rail above a reading view from a page. The snippets stay the page's, and are cleared when the page leaves.
	import type { Snippet } from 'svelte';
	import { acts } from './acts.svelte';

	let { lead, acts: controls }: { lead?: Snippet; acts?: Snippet } = $props();

	$effect(() => {
		acts.lead = lead ?? null;
		acts.acts = controls ?? null;
		return () => {
			acts.lead = null;
			acts.acts = null;
		};
	});
</script>
