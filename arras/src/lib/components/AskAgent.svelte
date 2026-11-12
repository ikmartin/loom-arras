<script lang="ts">
	// "Ask an agent" for a work with no overview (plan 0.24.3): a person's annotation on the whole work asking that it be read through and its overview written (`review/ask.ts`). Once asked, it says when until an overview is written. `quiet` keeps the refusal and the earlier ask to a tooltip, for the status line, where the overview's own section says them in full.
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { Reference } from '$lib/manifest/types';
	import { askOverview, askedFor } from '$lib/review/ask';
	import { when } from '$lib/sessions/when';
	import { can } from '$lib/write';

	let { citekey, ref, quiet = false, test = 'ask-agent' }: { citekey: string; ref: Reference; quiet?: boolean; test?: string } = $props();

	let serves = $state(false);
	onMount(() => {
		void can('annotate').then((yes) => (serves = yes));
	});

	const m = $derived(store.manifest);
	const asked = $derived(askedFor(m, citekey));
	const earlier = $derived(asked ? `asked ${when(asked.created)}` : '');
	let busy = $state(false);
	let refused = $state('');

	async function ask(): Promise<void> {
		busy = true;
		refused = await askOverview(citekey);
		busy = false;
	}
</script>

{#if serves && !ref.overview}
	<span class="ask">
		{#if asked && !quiet}<span class="asked" data-testid="{test}-asked">{earlier}</span>{/if}
		<button type="button" class="act" data-testid={test} disabled={busy} title={asked ? `${earlier[0].toUpperCase()}${earlier.slice(1)}; asking again leaves another annotation` : 'Leaves an annotation on this work asking an agent to read it through and write its overview'} onclick={ask}>
			{asked ? 'Ask again' : 'Ask an agent'}
		</button>
		{#if refused}<span class="refused" role="status">{refused}</span>{/if}
	</span>
{/if}

<style>
	.ask {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 8px;
	}
	.act {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		color: var(--link);
		cursor: pointer;
	}
	.act:hover:not(:disabled) {
		text-decoration: underline;
	}
	.act:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
	.asked {
		color: var(--ink-faint);
	}
	.refused {
		color: var(--state-stale);
	}
</style>
