<script lang="ts">
	// Review › Incoming: what waits to be taken in — a collaborator's fetched pull, and an agent's copy of a document — one at a time, chosen from one list, each reviewed in one pass (plan 0.25.2). The answer to the last act stays on the page after its contribution is gone, so what was taken is still said.
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { can } from '$lib/write';
	import ContributionReview from '$lib/review/ContributionReview.svelte';
	import IncomingPull from '$lib/review/IncomingPull.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';
	import type { AdoptionReview } from '$lib/manifest/types';

	const m = $derived(store.manifest!);
	const adoptions = $derived((m.contributions ?? []).filter((x): x is AdoptionReview => x.kind === 'adopt'));
	let source = $state('');
	let sync = $state(false);
	// the last answer and the contribution it came from: said by that contribution's bar while it is shown, and by the page once it is not (taken in whole, or another chosen)
	let answer = $state<{ text: string; refused: boolean; from: string } | null>(null);
	const chosen = $derived(adoptions.some((x) => x.copy === source) ? source : m.incoming ? '' : (adoptions[0]?.copy ?? ''));
	const adoption = $derived(adoptions.find((x) => x.copy === chosen));
	const pullLabel = $derived(m.contributions?.find((c) => c.kind === 'workspace')?.label ?? `Pull from ${m.incoming?.workspace}`);
	const showing = $derived(adoption?.copy ?? (m.incoming ? 'pull' : ''));
	onMount(() => {
		void can('sync-incorporate').then((yes) => (sync = yes));
	});
	function pick(value: string): void {
		source = value;
		answer = null;
	}
</script>

<main class="page" data-testid="incoming">
	<ReviewHeading title="Incoming" />
	{#if adoptions.length + (m.incoming ? 1 : 0) > 1}
		<label class="pick">Contribution
			<select value={chosen} onchange={(e) => pick(e.currentTarget.value)} data-testid="contribution-pick">
				{#if m.incoming}<option value="">{pullLabel}</option>{/if}
				{#each adoptions as a (a.copy)}<option value={a.copy}>{a.label}</option>{/each}
			</select>
		</label>
	{/if}
	{#if answer && answer.from !== showing}<div class="answer"><Said text={answer.text} refused={answer.refused} testid="incoming-said" /></div>{/if}
	{#if adoption}
		{@const copy = adoption.copy}
		{#key copy}<ContributionReview contribution={adoption} onanswer={(a) => (answer = a && { ...a, from: copy })} />{/key}
	{:else if m.incoming}
		{#key m.incoming.commit}<IncomingPull incoming={m.incoming} label={pullLabel} writable={sync} onanswer={(a) => (answer = a && { ...a, from: 'pull' })} />{/key}
	{:else}
		<Empty text="Nothing waits to be taken in." testid="incoming-none" />
	{/if}
</main>

<style>
	.pick {
		display: flex;
		align-items: center;
		gap: var(--gap-tight);
		margin-bottom: var(--gap);
		font-size: 13px;
	}
	.answer {
		margin-bottom: var(--gap);
	}
	.pick select {
		max-width: 100%;
		font: inherit;
	}
</style>
