<script lang="ts">
	// "Ask an agent" for a work with no overview (plan 0.24.3): a person's note on the whole work, in the selected session, asking that it be read through and its overview written. An agent hears of it as it hears of any note a person writes; the viewer starts no agent and loom calls no model. Once asked, it says when and where until an overview is written. `quiet` keeps the refusal and the earlier ask to a tooltip, for the status line, where the overview's own section says them in full.
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { Reference } from '$lib/manifest/types';
	import { ASK_OVERVIEW, askedFor, quote } from '$lib/notes';
	import NoSession from '$lib/sessions/NoSession.svelte';
	import { titleOf, writable } from '$lib/sessions/sessions.svelte';
	import { when } from '$lib/sessions/when';
	import { can } from '$lib/write';

	let { citekey, ref, quiet = false, test = 'ask-agent' }: { citekey: string; ref: Reference; quiet?: boolean; test?: string } = $props();

	let serves = $state(false);
	onMount(() => {
		void can('note').then((yes) => (serves = yes));
	});

	const m = $derived(store.manifest);
	const why = $derived(writable(m));
	const asked = $derived(askedFor(m, citekey));
	const where = $derived.by(() => {
		const s = asked && (m?.sessions ?? []).find((x) => x.id === asked.session);
		return s ? titleOf(s) : '';
	});
	const earlier = $derived(asked ? `asked ${when(asked.when)}${where ? ` in ${where}` : ''}` : '');
	let busy = $state(false);
	let refused = $state('');

	async function ask(): Promise<void> {
		busy = true;
		refused = await quote({ target: citekey, body: ASK_OVERVIEW });
		busy = false;
	}
</script>

{#if serves && !ref.overview}
	<span class="ask">
		{#if asked && !quiet}<span class="asked" data-testid="{test}-asked">{earlier}</span>{/if}
		<button type="button" class="act" data-testid={test} disabled={!!why || busy} title={why || (asked ? `${earlier[0].toUpperCase()}${earlier.slice(1)}; asking again leaves another note` : 'Leaves a note on this work asking an agent to read it through and write its overview')} onclick={ask}>
			{asked ? 'Ask again' : 'Ask an agent'}
		</button>
		{#if why && !quiet}<NoSession />{/if}
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
