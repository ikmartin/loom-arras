<script lang="ts">
	// A labelled list in the right rail (book 15.3.2). Every rail section is one of these, so they read alike and an empty one disappears rather than showing "None".
	import type { Snippet } from 'svelte';

	let { label, empty = '', children }: { label: string; empty?: string; children?: Snippet } = $props();
</script>

<section class="rail-section">
	<p class="rail-label">{label}</p>
	{#if children}
		{@render children()}
	{:else if empty}
		<p class="none">{empty}</p>
	{/if}
</section>

<style>
	.rail-section {
		margin-bottom: var(--gap);
	}
	.none {
		font-size: 11px;
		color: var(--ink-faint);
		margin: 0;
	}
</style>
