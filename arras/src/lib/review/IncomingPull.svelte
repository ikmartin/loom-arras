<script lang="ts">
	// A collaborator's fetched pull in Incoming (plan 0.25.2), laid out as an agent's copy is: its changes named and listed, one at a time beneath a bar that never moves, "accept as checked" for each block of mathematics, and one Apply. A pull is taken whole, since loom applies it as one patch; whatever loom answers is said in the bar.
	import ActionBar from './ActionBar.svelte';
	import Said from './Said.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { IncorporationMathReview, IncorporationOutcome, IncomingReview } from '$lib/manifest/types';
	import { displayNode } from '$lib/nodes/display';
	import { write } from '$lib/write';
	import { untrack } from 'svelte';
	import { acceptFor } from './contribution';

	let { incoming, label, writable, onanswer }: { incoming: IncomingReview; label: string; writable: boolean; onanswer?: (a: { text: string; refused: boolean } | null) => void } = $props();
	// the last answer, said in the bar and handed to the page, which keeps saying it once the pull is gone
	let answer = $state<{ text: string; refused: boolean } | null>(null);
	function say(a: { text: string; refused: boolean } | null): void {
		answer = a;
		onanswer?.(a);
	}

	let index = $state(0);
	let busy = $state('');
	let review = $state<IncorporationMathReview | null>(null);
	let checked = $state<string[]>([]);
	const identity = $derived(JSON.stringify([incoming.commit, incoming.base, store.manifest?.reviewer?.name]));
	// the pull's changed passages, and any block its mathematics review adds because something it rests on changed
	const passages = $derived([...incoming.changes, ...(review?.items.filter((r) => !incoming.changes.some((c) => c.key === r.key)).map((r) => ({ key: r.key, name: r.name, kind: 'edited' as const, category: undefined, conflict: false, local: null, incoming: null, current: '', proposed: '', incoming_macros: '', affected: [], local_changed: false, already_local: false })) ?? [])]);
	const change = $derived(passages[Math.min(index, passages.length - 1)]);
	const math = $derived(review?.items.find((r) => r.key === change?.key));
	const clash = $derived(incoming.changes.some((c) => c.conflict));
	const blocked = $derived(!!incoming.issues?.length || clash);
	const title = (key: string, name?: string | null) => name ?? displayNode(store.manifest!, key).name;
	$effect(() => {
		void identity;
		if (writable) untrack(() => void prepare());
	});

	async function prepare(): Promise<void> {
		const started = identity;
		busy = 'prepare';
		review = null;
		checked = [];
		const done = await write('sync-preview', { incoming: incoming.commit, base: incoming.base });
		if (started !== identity) return;
		if (done.ok) review = done.result as unknown as IncorporationMathReview;
		else say({ text: done.error?.message ?? 'Loom could not prepare the pull for review.', refused: true });
		busy = '';
	}
	function toggle(key: string, on: boolean): void {
		checked = on ? [...new Set([...checked, key])] : checked.filter((k) => k !== key);
	}
	async function apply(): Promise<void> {
		busy = 'apply';
		say(null);
		const accept = review ? acceptFor(review, checked, {}) : [];
		const done = await write('sync-incorporate', { incoming: incoming.commit, base: incoming.base, ...(review ? { review_token: review.token, accept } : {}) });
		if (done.ok) {
			const o = done.result as unknown as IncorporationOutcome;
			say({ text: o.acceptance_error ?? `Took the pull: ${o.accepted?.length ?? 0} accepted, ${o.pending?.length ?? 0} wait in Needs review. Each document it changed is kept as it was first.`, refused: false });
			await store.refresh();
		} else say({ text: done.error?.message ?? 'Loom did not take the pull.', refused: true });
		busy = '';
	}
</script>

<section class="contribution" data-testid="pull">
	<ActionBar testid="contribution-bar" said={answer?.text ?? ''} refused={answer?.refused}>
		{#snippet lead()}
			<b>{label}</b> · {passages.length} {passages.length === 1 ? 'change' : 'changes'} · {checked.length} marked as checked
		{/snippet}
		{#snippet actions()}
			{#if writable}<button class="btn primary" disabled={!!busy || blocked} onclick={apply} data-testid="apply">{busy === 'apply' ? 'Applying…' : 'Apply the pull'}</button>{/if}
		{/snippet}
		{#snippet below()}
			<div class="step">
				<button class="btn small quiet" disabled={index <= 0} onclick={() => index--} aria-label="Previous change" data-testid="prev-change">‹</button>
				<span class="at" data-testid="change-at">{passages.length ? index + 1 : 0} of {passages.length}</span>
				<button class="btn small quiet" disabled={index >= passages.length - 1} onclick={() => index++} aria-label="Next change" data-testid="next-change">›</button>
				<span class="now">{change ? title(change.key, change.name) : ''}</span>
				{#if writable && math && !math.unavailable}
					<label class="accept" title="Records your acceptance of this block's mathematics as it is written in, when you apply"><input type="checkbox" checked={checked.includes(math.key)} disabled={!!busy} onchange={(e) => toggle(math.key, e.currentTarget.checked)} data-testid="accept-checked" /> accept as checked</label>
				{/if}
				<span class="whole">A pull is taken whole.</span>
			</div>
		{/snippet}
	</ActionBar>
	<p class="lead">A revision fetched from {incoming.workspace}, {incoming.branch}. Apply writes all of it into your documents, keeping each as it was first. {#if busy === 'prepare'}Preparing its mathematics for review…{/if}</p>
	{#each incoming.issues ?? [] as issue, i (i)}<Said text={issue} refused />{/each}
	{#if clash}<Said text="You and the collaborator both changed a passage and the edits clash; reconcile it in the workspace, then fetch again." refused />{/if}
	<div class="workspace">
		<aside aria-label="The pull's changes">
			{#each passages as c, i (c.key)}
				<button class="row" class:active={i === index} onclick={() => (index = i)} data-testid="change-row" data-key={c.key}>
					<span class="name">{title(c.key, c.name)}</span><small>{c.category === 'prose' ? 'prose' : checked.includes(c.key) ? 'accept as checked' : c.conflict ? 'clashes' : review && !review.items.some((r) => r.key === c.key) ? 'source only' : 'to review'}</small>
				</button>
			{/each}
		</aside>
		<div class="change" data-testid="change-shown">
			{#if change}
				<h2>{title(change.key, change.name)}</h2>
				{#if math}
					<p class="detail">{math.reason}</p>
					<div class="pair">
						<div><h4>Yours</h4>{#if math.local}<Fragment path={math.local.path} previewMacros={math.local.macros} isolatedMacros />{:else}<p class="muted">New in this pull.</p>{/if}</div>
						<div><h4>After the pull</h4><Fragment path={math.proposed.path} previewMacros={math.proposed.macros} isolatedMacros /></div>
					</div>
					{#if math.unavailable}<p class="detail">{math.unavailable} It stays in Needs review.</p>{/if}
				{:else}
					{#if change.conflict}<p class="detail">You and the collaborator both changed it, and the edits clash.</p>{/if}
					<div class="pair">
						<div><h4>Yours</h4>{#if change.local}<Fragment path={change.local} />{:else}<pre>{change.current || 'Not in your document.'}</pre>{/if}</div>
						<div><h4>The pull's</h4>{#if change.incoming}<Fragment path={change.incoming} macroSet={change.incoming_macros} isolatedMacros />{:else}<pre>{change.proposed || 'Removed.'}</pre>{/if}</div>
					</div>
					{#if change.category === 'prose'}<p class="detail">Prose between results needs no acceptance.</p>{/if}
				{/if}
			{/if}
			<details><summary>The files the pull changes ({incoming.files.length})</summary>{#each incoming.files as f (f.path)}<details><summary>{f.path} · {f.status}</summary>{#if f.diff}<pre>{f.diff}</pre>{:else}<p class="muted">No text diff for this file.</p>{/if}</details>{/each}</details>
		</div>
	</div>
</section>

<style>
	.step {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight);
		font-size: 12.5px;
	}
	.at {
		font-variant-numeric: tabular-nums;
		color: var(--ink-soft);
	}
	.now {
		flex: 1;
		min-width: 8em;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.accept,
	.whole {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--ink-soft);
	}
	.lead {
		color: var(--ink-soft);
		font-size: 13px;
	}
	.workspace {
		display: grid;
		grid-template-columns: 220px minmax(0, 1fr);
		gap: var(--gap-wide);
		align-items: start;
	}
	aside {
		border-right: 1px solid var(--rule);
		padding-right: var(--gap);
	}
	.row {
		all: unset;
		box-sizing: border-box;
		display: block;
		width: 100%;
		padding: 4px 6px;
		border-radius: var(--rad-pill);
		cursor: pointer;
		font-size: 12.5px;
	}
	.row:hover {
		background: var(--sheet);
	}
	.row.active {
		background: var(--link-wash);
	}
	.row .name {
		display: block;
		overflow-wrap: anywhere;
	}
	.row small {
		color: var(--ink-faint);
	}
	.change {
		min-width: 0;
	}
	.change h2 {
		font: 400 21px/1.3 Georgia, serif;
		margin: 0;
	}
	.detail {
		margin: 4px 0;
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.pair {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--gap-wide);
		margin-top: var(--gap);
	}
	.pair > div + div {
		border-left: 1px solid var(--rule);
		padding-left: var(--gap-wide);
	}
	.pair h4 {
		margin: 0 0 6px;
		font-size: 11.5px;
		font-weight: 500;
		color: var(--ink-faint);
	}
	.pair :global(.review-changed) {
		background: var(--state-accepted-wash);
	}
	pre {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		font-size: 12px;
	}
	details {
		margin: var(--gap) 0;
		font-size: 12.5px;
	}
	@media (max-width: 1100px) {
		.workspace {
			grid-template-columns: 1fr;
		}
		aside {
			border-right: 0;
			max-height: 30vh;
			overflow-y: auto;
		}
	}
	@media (max-width: 560px) {
		.pair {
			grid-template-columns: 1fr;
		}
		.pair > div + div {
			border-left: 0;
			padding-left: 0;
		}
	}
</style>
