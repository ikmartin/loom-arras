<script lang="ts">
	// One answer to an act, said where the act was made: a done act is a status, a refusal an alert, and it stays until the next act there.
	let { text, refused = false, testid }: { text: string; refused?: boolean; testid?: string } = $props();
</script>

<p class="said" class:refused role={refused ? 'alert' : 'status'} data-testid={testid}>{text}</p>

<style>
	.said {
		margin: 0;
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.said.refused {
		color: var(--state-incomplete);
	}
</style>
