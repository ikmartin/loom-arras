<script lang="ts">
	// What a Review page says when nothing waits there: one sentence, and the one thing worth doing next when there is one.
	import type { Snippet } from 'svelte';

	let { text, action, testid }: { text: string; action?: Snippet; testid?: string } = $props();
</script>

<div class="empty" data-testid={testid}>
	<p>{text}</p>
	{#if action}{@render action()}{/if}
</div>

<style>
	.empty {
		margin: var(--gap-wide) 0;
		color: var(--ink-soft);
		font-size: 13.5px;
	}
	.empty p {
		margin: 0 0 var(--gap-tight);
	}
</style>
