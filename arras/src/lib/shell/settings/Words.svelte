<script lang="ts">
	// A setting's words, with what stands in backticks set as code.
	let { text }: { text: string } = $props();
	const parts = $derived(text.split(/`([^`]+)`/));
</script>

{#each parts as part, i (i)}{#if i % 2}<code>{part}</code>{:else}{part}{/if}{/each}
