<script lang="ts">
	// The proposed results waiting for the author, across the library (WQ-55): one queue, grouped by work, each work's count beside it, and one result at a time at full width. ↑ ↓ move through it; v verifies, e edits and d discards the one shown; after a verb the queue moves to the next. `?work=` opens it at that work's first, which a work's Digest view and the ledger link to.
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { bibText, surnames } from '$lib/works';
	import { can } from '$lib/write';
	import ProposalCard from './ProposalCard.svelte';
	import type { ResultRecord } from '$lib/manifest/types';

	interface Waiting {
		id: string;
		citekey: string;
		record: ResultRecord;
	}

	const m = $derived(store.manifest!);
	const title = (ck: string) => bibText(m.references[ck]?.bib.title) || ck;
	// grouped by work, the works by title, a work's results by page then id
	const queue = $derived.by(() => {
		const out: Waiting[] = [];
		for (const [ck, ref] of Object.entries(m.references ?? {})) {
			for (const [id, record] of Object.entries(ref.results ?? {})) if (record.state === 'proposed') out.push({ id, citekey: ck, record });
		}
		return out.sort((a, b) => title(a.citekey).localeCompare(title(b.citekey)) || a.citekey.localeCompare(b.citekey) || (a.record.page ?? 0) - (b.record.page ?? 0) || a.id.localeCompare(b.id));
	});
	const works = $derived([...new Set(queue.map((x) => x.citekey))].map((ck) => ({ ck, n: queue.filter((x) => x.citekey === ck).length })));

	let writable = $state(false);
	onMount(() => void can('library-verify').then((ok) => (writable = ok)));

	// the result shown, by id; when it leaves the queue (verified, discarded) the one now at its place is shown
	let shown = $state('');
	let at = $state(0);
	const asked = $derived(page.url.searchParams.get('work') ?? '');
	$effect(() => {
		if (shown || !queue.length) return;
		const first = asked ? queue.findIndex((x) => x.citekey === asked) : 0;
		at = Math.max(0, first);
		shown = queue[at]?.id ?? '';
	});
	const index = $derived.by(() => {
		const i = queue.findIndex((x) => x.id === shown);
		return i >= 0 ? i : Math.min(at, queue.length - 1);
	});
	const current = $derived(queue[index]);
	function go(i: number): void {
		if (!queue.length) return;
		at = (i + queue.length) % queue.length;
		shown = queue[at].id;
	}
	/** After a verb: the next one, which takes this one's place once the manifest drops it. */
	function acted(): void {
		at = index;
		shown = queue[index + 1]?.id ?? queue[index - 1]?.id ?? '';
	}

	let card = $state<ProposalCard | null>(null);
	function keys(e: KeyboardEvent): void {
		if ((e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable]') || e.metaKey || e.ctrlKey || e.altKey) return;
		if (e.key === 'ArrowDown') go(index + 1);
		else if (e.key === 'ArrowUp') go(index - 1);
		else if (writable && e.key === 'v') card?.verify();
		else if (writable && e.key === 'e') card?.edit();
		else if (writable && e.key === 'd') card?.discard();
		else return;
		e.preventDefault();
	}
</script>

{#if queue.length}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<section class="queue" id="queue" data-testid="proposal-queue" tabindex="0" aria-label="proposed results waiting for you; ↑ ↓ to move, v e d to verify, edit or discard" onkeydown={keys}>
		<header>
			<h2>Proposed results <span class="n">{queue.length}</span></h2>
			<span class="steps">
				<button type="button" aria-label="Previous proposal" onclick={() => go(index - 1)} data-testid="queue-prev">‹</button>
				<span data-testid="queue-at">{index + 1} of {queue.length}</span>
				<button type="button" aria-label="Next proposal" onclick={() => go(index + 1)} data-testid="queue-next">›</button>
			</span>
		</header>
		<ul class="works" data-testid="queue-works">
			{#each works as w (w.ck)}
				<li>
					<button type="button" class:on={current?.citekey === w.ck} aria-pressed={current?.citekey === w.ck} onclick={() => go(queue.findIndex((x) => x.citekey === w.ck))} data-testid="queue-work-{w.ck}"
						>{surnames(m.references[w.ck]?.bib.author) || w.ck}, {title(w.ck)} <span class="n">{w.n}</span></button
					>
				</li>
			{/each}
		</ul>
		{#if current}
			{#key current.id}<ProposalCard bind:this={card} id={current.id} record={current.record} citekey={current.citekey} {writable} onacted={acted} />{/key}
		{/if}
	</section>
{/if}

<style>
	.queue {
		margin: 0 0 var(--gap-wide);
		outline: none;
	}
	.queue:focus-visible {
		box-shadow: 0 0 0 2px var(--link-wash);
		border-radius: var(--rad-control);
	}
	header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--gap);
	}
	h2 {
		margin: 0;
		font-size: 1.05rem;
	}
	.n {
		font-size: 0.8em;
		color: var(--ink-soft);
		font-variant-numeric: tabular-nums;
	}
	.steps {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-family: var(--sans);
		font-size: 12px;
		font-variant-numeric: tabular-nums;
	}
	.steps button {
		font: inherit;
		font-size: 15px;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.works {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		list-style: none;
		margin: var(--gap-tight) 0;
		padding: 0;
	}
	.works button {
		font: inherit;
		font-size: 11.5px;
		color: var(--ink-soft);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 1px 10px;
		cursor: pointer;
		max-width: 28rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.works button.on {
		color: var(--link);
		border-color: var(--link);
		background: var(--link-wash);
	}
</style>
