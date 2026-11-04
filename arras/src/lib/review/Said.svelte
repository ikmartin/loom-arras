<script lang="ts">
	// One answer to an act, said where the act was made: a done act is a status, a refusal an alert, and it stays until the next act there. An answer of several lines, as loom gives several reasons at once, is a list, one reason a line.
	let { text, refused = false, testid }: { text: string; refused?: boolean; testid?: string } = $props();
	const lines = $derived(text.split('\n').map((l) => l.trim()).filter(Boolean));
</script>

{#if lines.length > 1}
	<ul class="said" class:refused role={refused ? 'alert' : 'status'} data-testid={testid}>
		{#each lines as line, i (i)}<li>{line}</li>{/each}
	</ul>
{:else}
	<p class="said" class:refused role={refused ? 'alert' : 'status'} data-testid={testid}>{text}</p>
{/if}

<style>
	.said {
		margin: 0;
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	ul.said {
		padding-left: 1.2em;
		max-height: 30vh;
		overflow-y: auto;
	}
	.said.refused {
		color: var(--state-incomplete);
	}
</style>
