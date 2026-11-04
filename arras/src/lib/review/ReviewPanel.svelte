<script lang="ts">
	// Beside a document opened from Your Changes (`?review=KEY`), inside the document's side panel: the block, why it waits, the change when it changed since it was accepted, and Accept, its answer said here. A block loom cannot accept says why instead.
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { can, write } from '$lib/write';
	import { displayNode } from '$lib/nodes/display';
	import { reviewUrl } from '$lib/nav';
	import { shortDate } from '$lib/badges';
	import { here } from '$lib/here.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import { causeLabel } from './evidence';
	import { takenLabel } from './queue';
	import Said from './Said.svelte';

	let { reviewKey, causeIndex, master, plain, causeHref }: { reviewKey: string; causeIndex: number; master: string; plain: string; causeHref: (i: number) => string } = $props();

	const m = $derived(store.manifest!);
	const key = $derived(m.keys[reviewKey]);
	const row = $derived((m.unresolved ?? []).find((r) => r.key === reviewKey));
	const causes = $derived(key?.acceptance?.causes ?? []);
	const cause = $derived(causes[causeIndex] ?? causes[0]);
	const comparison = $derived(cause?.comparison);
	const acceptedSide = $derived(cause?.kind === 'own-text-changed');
	const name = $derived(displayNode(m, reviewKey, master).name);
	let served = $state(false);
	let busy = $state(false);
	let said = $state<{ text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('review-accept').then((yes) => (served = yes));
	});
	// the block under review and why, for `loom here`
	$effect(() => {
		here.review = { key: reviewKey, cause: cause ? causeLabel(m, cause) : null };
		return () => {
			here.review = null;
		};
	});

	const lower = (t: string) => t.charAt(0).toLowerCase() + t.slice(1);
	const status = $derived(
		!row
			? key?.acceptance?.fresh
				? `Accepted by ${key.acceptance.author}, ${shortDate(key.acceptance.date)}.`
				: 'Not waiting in Your Changes.'
			: row.cause === 'never-accepted'
				? 'Never accepted.'
				: row.cause === 'earlier-change'
					? 'Changed since you accepted it.'
					: `${takenLabel(row)}.`
	);

	async function accept(): Promise<void> {
		busy = true;
		said = null;
		const done = (await write('review-accept', { keys: [reviewKey] })) as Awaited<ReturnType<typeof write>> & { accepted?: string[]; refused?: { why: string }[] };
		if (!done.ok) said = { text: done.error?.message ?? 'The publisher refused it.', refused: true };
		else {
			await store.refresh();
			said = done.accepted?.length ? { text: `Accepted ${name}.`, refused: false } : { text: done.refused?.[0]?.why ?? 'Not accepted.', refused: true };
		}
		busy = false;
	}
</script>

<div class="panel">
	<header><strong>{name}</strong><a href={plain}>close</a></header>
	<p class="status" data-testid="review-panel-status">{status}</p>
	{#if causes.length > 1}
		<select aria-label="Reason for review" value={causes.indexOf(cause)} onchange={(e) => goto(causeHref(Number(e.currentTarget.value)), { noScroll: true, keepFocus: true })}>{#each causes as c, i (i)}<option value={i}>{causeLabel(m, c)} · {i + 1} of {causes.length}</option>{/each}</select>
	{:else if cause}<p class="why">{causeLabel(m, cause)}</p>{/if}
	{#if comparison}
		<div data-testid="review-comparison">
			<h4>{acceptedSide ? 'Last accepted' : 'Current'} · {cause?.id ?? reviewKey}</h4>
			<Fragment path={acceptedSide ? comparison.accepted : comparison.current} macroSet={acceptedSide ? comparison.accepted_macros : ''} isolatedMacros={acceptedSide} />
		</div>
	{:else if cause?.diff}<DiffView path={cause.diff} />{/if}
	{#if row?.refusal}<p class="cannot" data-testid="review-panel-refusal">Can't be accepted yet: {lower(row.refusal)}</p>
	{:else if row && served && m.reviewer?.name}<button class="btn primary" disabled={busy} onclick={() => void accept()} data-testid="review-panel-accept">{busy ? 'Accepting…' : 'Accept'}</button>{/if}
	{#if said}<Said text={said.text} refused={said.refused} testid="review-panel-said" />{/if}
	<p><a href={reviewUrl(master, reviewKey)} data-testid="review-panel-back">Back to Your Changes</a></p>
</div>

<style>
	.status,
	.why,
	.cannot {
		font-size: 13px;
		margin: 0 0 var(--gap-tight);
	}
	.why,
	.cannot {
		color: var(--ink-soft);
	}
	h4 {
		margin: var(--gap-tight) 0;
		font-size: 12.5px;
		font-weight: 500;
		color: var(--ink-soft);
	}
	select {
		max-width: 100%;
		margin-bottom: var(--gap-tight);
	}
</style>
