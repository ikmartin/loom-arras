<script lang="ts">
	// Why a write is refused, said beside the control that refused it (plan 0.13.3 S6, DR-230-ikmartin). The control is disabled and this sentence stands next to it for as long as the refusal holds: a disabled control that explains nothing leaves the reader guessing which of the two problems they have, and the panel's footer carries only the state.
	import { store } from '$lib/manifest/client.svelte';
	import { writable } from './sessions.svelte';

	const why = $derived(writable(store.manifest));
</script>

{#if why}<span class="refusal" role="status" data-testid="no-session-tip">{why}</span>{/if}

<style>
	.refusal {
		font-family: var(--sans);
		font-size: 12.5px;
		line-height: 1.4;
		color: var(--state-stale);
	}
</style>
