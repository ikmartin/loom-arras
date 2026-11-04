<script lang="ts">
	// Review › Suggestions: what someone proposed changing. Those with text to put in come first, each with its change shown and Apply, which writes it into its file, a version of the document kept first, and resolves it as applied; they are what Review counts. Those in prose alone follow, to weigh: resolved once acted on, or dismissed when they should not have been raised. Each says the document it is on and who wrote it, and opens there at its place (V7). An act's answer is said in its row while the row stands, else in the bar with its undo.
	import '$lib/review/review.css';
	import { onMount } from 'svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { Annotation } from '$lib/manifest/types';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { placeUrl } from '$lib/nav';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';
	import { documentOf, toApply, toConsider, writerOf } from '$lib/review/suggestions';
	import { keyName } from '$lib/workspace/names';
	import { can, write } from '$lib/write';

	const m = $derived(store.manifest!);
	const applying = $derived(toApply(m));
	const weighing = $derived(toConsider(m));
	let served = $state<Record<string, boolean>>({});
	onMount(() => {
		for (const e of ['suggestion-apply', 'resolve', 'discard']) void can(e).then((yes) => (served = { ...served, [e]: yes }));
	});

	// what is running and where its answer goes: a suggestion's id, or '*' for the bar once its row has gone
	let busy = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	let undo = $state<{ endpoint: 'resolve' | 'discard'; id: string; name: string } | null>(null);
	let asking = $state('');
	let reason = $state('');

	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');
	const name = (a: Annotation) => keyName(m, a.target.key);
	const listed = (id: string) => [...toApply(store.manifest!), ...toConsider(store.manifest!)].some((x) => x.id === id);

	/** One act on suggestion `a`; `past` is what its answer says when the publisher's own words would name it by id. */
	async function act(a: Annotation, endpoint: string, body: Record<string, unknown>, past?: string): Promise<void> {
		busy = a.id;
		said = null;
		undo = null;
		const done = await write(endpoint, { annotation: a.id, ...body });
		if (done.ok) await store.refresh();
		const text = done.ok ? capital(past ?? done.result ?? 'done') : (done.error?.message ?? 'The publisher refused it.');
		said = { at: done.ok && !listed(a.id) ? '*' : a.id, text, refused: !done.ok };
		if (done.ok && (endpoint === 'resolve' || endpoint === 'discard') && !body.undo) undo = { endpoint, id: a.id, name: name(a) };
		busy = '';
		asking = '';
		reason = '';
	}
	async function takeBack(): Promise<void> {
		const u = undo!;
		busy = '*';
		undo = null;
		const done = await write(u.endpoint, { annotation: u.id, undo: true });
		if (done.ok) await store.refresh();
		said = { at: '*', text: done.ok ? `Put the suggestion on ${u.name} back.` : (done.error?.message ?? 'The publisher refused it.'), refused: !done.ok };
		busy = '';
	}
	const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
</script>

{#snippet row(a: Annotation)}
	{@const where = documentOf(m, a)}
	{@const text = a.payload !== null && a.payload !== undefined}
	<li class="suggestion" data-testid="suggestion" data-id={a.id}>
		<div class="line">
			<a href={placeUrl(m, a.target.key, a.id, a.in)} data-testid="suggestion-open">{name(a)}</a>
			{#if where?.words}<span class="where" data-testid="suggestion-document">{where.words}</span>{/if}
			<span class="faint" data-testid="suggestion-writer">· {writerOf(m, a)}{a.severity ? ` · ${a.severity}` : ''}</span>
			<span class="acts">
				{#if text && served['suggestion-apply'] && a.change?.state === 'ready' && !where?.copy}
					<button type="button" class="btn small primary" disabled={!!busy} title="Write it into the file; a version of the document is kept first" data-testid="suggestion-apply" onclick={() => void act(a, 'suggestion-apply', {})}>{busy === a.id ? 'Applying…' : 'Apply'}</button>
				{/if}
				{#if text && served.resolve && a.change?.state === 'taken'}
					<button type="button" class="btn small" disabled={!!busy} title="The text reads as it taken; that is recorded" data-testid="suggestion-applied" onclick={() => void act(a, 'resolve', { applied: true }, `Resolved the suggestion on ${name(a)} as applied`)}>Resolve as applied</button>
				{/if}
				{#if served.resolve}
					<button type="button" class="btn small" disabled={!!busy} title="You have acted on it" data-testid="suggestion-resolve" onclick={() => void act(a, 'resolve', {}, `Resolved the suggestion on ${name(a)}`)}>Resolve</button>
				{/if}
				{#if served.discard}
					<button type="button" class="btn small quiet" disabled={!!busy} title="It should not have been raised" data-testid="suggestion-dismiss" onclick={() => ((asking = a.id), (reason = ''), (said = null))}>Dismiss…</button>
				{/if}
			</span>
		</div>
		{#if a.quote}<q class="quoted" data-testid="suggestion-quote"><TexProse text={a.quote} /></q>{/if}
		<Prose html={a.body_html} />
		{#if text}
			{#if a.change?.state === 'ready'}<DiffView path={a.change.diff} />
			{:else if a.change?.state === 'unplaced'}<p class="why" data-testid="suggestion-unplaced">It cannot be put in as it stands: {a.change.why}.</p>
			{:else if a.change?.state === 'taken'}<p class="why">The text already reads as it taken.</p>{/if}
			{#if where?.copy}<p class="why" data-testid="suggestion-on-copy">It is on the agent's copy, and comes in with the copy.</p>{/if}
		{/if}
		{#if asking === a.id}
			<div class="ask" data-testid="suggestion-ask">
				<!-- svelte-ignore a11y_autofocus -->
				<input bind:value={reason} placeholder="Why it should not have been raised, optionally" aria-label="Why it is dismissed" autofocus data-testid="suggestion-reason" onkeydown={(e) => e.key === 'Enter' && void act(a, 'discard', { reason: reason.trim() || undefined }, `Dismissed the suggestion on ${name(a)}`)} />
				<button type="button" class="btn small primary" disabled={!!busy} data-testid="suggestion-dismiss-go" onclick={() => void act(a, 'discard', { reason: reason.trim() || undefined }, `Dismissed the suggestion on ${name(a)}`)}>Dismiss</button>
				<button type="button" class="btn small quiet" onclick={() => (asking = '')}>Cancel</button>
			</div>
		{/if}
		{#if said?.at === a.id}<Said text={said.text} refused={said.refused} testid="suggestion-said" />{/if}
	</li>
{/snippet}

<main class="page review-page scrollbar-shown" data-testid="suggestions">
	<ReviewHeading title="Suggestions" />
	{#if !applying.length && !weighing.length}
		{#if said?.at === '*'}<Said text={said.text} refused={said.refused} testid="suggestions-bar-said" />{/if}
		<Empty text="No suggestion is open." testid="suggestions-none" />
	{:else}
		<ActionBar said={said?.at === '*' ? said.text : ''} refused={said?.refused} testid="suggestions-bar">
			{#snippet lead()}
				<span data-testid="suggestions-summary">{count(applying.length, 'to apply', 'to apply')} · {count(weighing.length, 'to consider', 'to consider')}</span>
			{/snippet}
			{#snippet actions()}
				{#if undo}<button type="button" class="btn small" disabled={!!busy} data-testid="suggestions-undo" onclick={() => void takeBack()}>Undo</button>{/if}
			{/snippet}
		</ActionBar>
		{#if applying.length}
			<section data-testid="suggestions-apply">
				<h2>To apply <span class="n">{applying.length}</span></h2>
				<p class="lead">Each proposes text. Apply writes it into the file, keeping a version of the document first.</p>
				<ul class="plain">
					{#each applying as a (a.id)}{@render row(a)}{/each}
				</ul>
			</section>
		{/if}
		{#if weighing.length}
			<section data-testid="suggestions-consider">
				<h2>To consider <span class="n">{weighing.length}</span></h2>
				<p class="lead">Each is prose, with no text to put in. Resolve it once you have acted on it, or dismiss it.</p>
				<ul class="plain">
					{#each weighing as a (a.id)}{@render row(a)}{/each}
				</ul>
			</section>
		{/if}
	{/if}
</main>

<style>
	h2 {
		font-size: 15px;
		font-weight: 500;
		margin: var(--gap-wide) 0 2px;
	}
	h2 .n,
	.where,
	.faint {
		color: var(--ink-soft);
		font-size: 12.5px;
		font-weight: 400;
	}
	.lead {
		margin: 0 0 var(--gap-tight);
		font-size: 13px;
		color: var(--ink-soft);
	}
	.suggestion {
		margin: var(--gap) 0;
		padding-bottom: var(--gap);
		border-bottom: 1px solid var(--rule);
	}
	.line {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 8px;
	}
	.acts {
		margin-left: auto;
		display: flex;
		gap: 6px;
	}
	.quoted {
		display: block;
		margin: 6px 0 2px;
		color: var(--ink-soft);
	}
	.why {
		margin: 4px 0 0;
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.ask {
		display: flex;
		gap: 6px;
		align-items: center;
		margin-top: 6px;
	}
	.ask input {
		font: inherit;
		flex: 1;
		padding: 3px 8px;
	}
</style>
