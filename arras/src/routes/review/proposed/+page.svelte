<script lang="ts">
	// Review › Proposed to you: everything someone proposes that the person decides, one card each. A copy, a pull or a work's proposed results is reviewed in its own pass, which the card opens here at its own address (`?copy=`, `?pull`, `?work=`). A suggestion with text and a citation are decided in their cards with Take it and Leave it, the suggestion's change shown: taking one writes it into its file, a version of the document kept first, and taking a citation keeps a reference note and writes no text. Prose suggestions follow, uncounted, resolved or dismissed. An act's answer is said in its card while the card stands, else in the bar with its undo.
	import '$lib/review/review.css';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import DiffView from '$lib/components/DiffView.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { Annotation } from '$lib/manifest/types';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { placeUrl, workUrl } from '$lib/nav';
	import { route } from '$lib/paths';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import ContributionReview from '$lib/review/ContributionReview.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import IncomingPull from '$lib/review/IncomingPull.svelte';
	import ProposalQueue from '$lib/review/ProposalQueue.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';
	import { itemsOf, tally } from '$lib/review/contribution';
	import { adoptionsOf, cardsOf, copySays, pullLabel, resultsOf } from '$lib/review/proposed';
	import { documentOf, toConsider, writerOf } from '$lib/review/suggestions';
	import NoSession from '$lib/sessions/NoSession.svelte';
	import { writable } from '$lib/sessions/sessions.svelte';
	import { keyName } from '$lib/workspace/names';
	import { bibText, surnames } from '$lib/works';
	import { can, write } from '$lib/write';

	const here = route('/review/proposed');
	/** How many of a card's changes it names before saying how many more. */
	const CHIPS = 12;

	const m = $derived(store.manifest!);
	const cards = $derived(cardsOf(m));
	const weighing = $derived(toConsider(m));
	const asked = $derived(page.url.searchParams);
	// what the address opens; one gone by the time it is asked for, as a copy taken in whole, leaves the list
	const adoption = $derived(adoptionsOf(m).find((x) => x.copy === asked.get('copy')));
	const pull = $derived(asked.has('pull') ? m.incoming : undefined);
	const queue = $derived(asked.has('work') && resultsOf(m).length > 0);
	const opened = $derived(!!adoption || !!pull || queue);
	const showing = $derived(adoption?.copy ?? (pull ? 'pull' : ''));

	let served = $state<Record<string, boolean>>({});
	onMount(() => {
		for (const e of ['suggestion-apply', 'resolve', 'discard', 'library-cite', 'sync-incorporate']) void can(e).then((yes) => (served = { ...served, [e]: yes }));
	});

	// the last answer from a copy or a pull: said by its bar while it is open, and by the list once it is not
	let answer = $state<{ text: string; refused: boolean; from: string } | null>(null);
	// what is running and where its answer goes: an annotation's id, or '*' for the bar once its card has gone
	let busy = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	let undo = $state<{ endpoint: 'resolve' | 'discard'; id: string; name: string } | null>(null);
	let asking = $state('');
	let reason = $state('');

	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');
	const name = (a: Annotation) => keyName(m, a.target.key);
	const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
	// a decision is recorded in a session, so without one there is none to make, and the page says so before anything is pressed
	const why = $derived(writable(m));
	const decides = $derived(!!(served['suggestion-apply'] || served.resolve || served['library-cite']));
	const file = (p: string) => p.split('/').pop()?.replace(/\.tex$/, '') ?? p;

	/** Whether annotation `id` is still drawn, on the list or folded in a copy's card. */
	function drawn(id: string): boolean {
		const now = store.manifest!;
		return toConsider(now).some((a) => a.id === id) || cardsOf(now).some((c) => c.id === id || (c.kind === 'copy' && c.suggestions.some((a) => a.id === id)));
	}

	/** One act on annotation `a`; `past` is what its answer says when the publisher's own words would name it by id. */
	async function act(a: Annotation, endpoint: string, body: Record<string, unknown>, past?: string): Promise<void> {
		busy = a.id;
		said = null;
		undo = null;
		const done = await write(endpoint, { annotation: a.id, ...body });
		if (done.ok) await store.refresh();
		const text = done.ok ? capital(past ?? done.result ?? 'done') : (done.error?.message ?? 'The publisher refused it.');
		said = { at: done.ok && !drawn(a.id) ? '*' : a.id, text, refused: !done.ok };
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
</script>

{#snippet chips(names: { name: string; bad: boolean }[])}
	<div class="chips" data-testid="proposed-chips">
		{#each names.slice(0, CHIPS) as c, i (i)}<span class="chip" class:bad={c.bad}>{c.name}</span>{/each}
		{#if names.length > CHIPS}<span class="more">and {names.length - CHIPS} more</span>{/if}
	</div>
{/snippet}

{#snippet suggestionHead(a: Annotation)}
	{@const where = documentOf(m, a)}
	<a class="name" href={placeUrl(m, a.target.key, a.id, a.in)} data-testid="suggestion-open">{name(a)}</a>
	{#if where?.words}<span class="of" data-testid="suggestion-document">{where.words}</span>{/if}
	<span class="of" data-testid="suggestion-writer">· {writerOf(m, a)}{a.severity ? ` · ${a.severity}` : ''}</span>
{/snippet}

{#snippet dismissing(a: Annotation)}
	{#if asking === a.id}
		<div class="ask" data-testid="suggestion-ask">
			<!-- svelte-ignore a11y_autofocus -->
			<input bind:value={reason} placeholder="Why it should not have been raised, optionally" aria-label="Why it is dismissed" autofocus data-testid="suggestion-reason" onkeydown={(e) => e.key === 'Enter' && void act(a, 'discard', { reason: reason.trim() || undefined }, `Dismissed the suggestion on ${name(a)}`)} />
			<button type="button" class="btn small primary" disabled={!!busy} data-testid="suggestion-dismiss-go" onclick={() => void act(a, 'discard', { reason: reason.trim() || undefined }, `Dismissed the suggestion on ${name(a)}`)}>Dismiss</button>
			<button type="button" class="btn small quiet" onclick={() => (asking = '')}>Cancel</button>
		</div>
	{/if}
{/snippet}

<!-- A suggestion with text. A copy's own are folded on its card, and come in with it, so there they can only be left. -->
{#snippet textSuggestion(a: Annotation)}
	{@const where = documentOf(m, a)}
	<div class="line">
		<span class="tag">a suggestion</span>
		{@render suggestionHead(a)}
		<span class="acts">
			{#if served['suggestion-apply'] && a.change?.state === 'ready' && !where?.copy}
				<button type="button" class="btn small primary" disabled={!!busy || !!why} title={why || 'Write it into the file; a version of the document is kept first'} data-testid="proposed-take" onclick={() => void act(a, 'suggestion-apply', {})}>{busy === a.id ? 'Taking…' : 'Take it'}</button>
			{/if}
			{#if served.resolve && a.change?.state === 'taken'}
				<button type="button" class="btn small" disabled={!!busy || !!why} title={why || 'The text reads as it taken; that is recorded'} data-testid="suggestion-applied" onclick={() => void act(a, 'resolve', { applied: true }, `Resolved the suggestion on ${name(a)} as applied`)}>Resolve as applied</button>
			{:else if served.resolve}
				<button type="button" class="btn small" disabled={!!busy || !!why} title={why || "You won't take it; the text is left as it is"} data-testid="proposed-leave" onclick={() => void act(a, 'resolve', {}, `Left the suggestion on ${name(a)}`)}>Leave it</button>
			{/if}
		</span>
	</div>
	{#if a.quote}<q class="quoted" data-testid="suggestion-quote"><TexProse text={a.quote} /></q>{/if}
	<Prose html={a.body_html} />
	{#if a.change?.state === 'ready'}<DiffView path={a.change.diff} />
	{:else if a.change?.state === 'unplaced'}<p class="why" data-testid="suggestion-unplaced">It cannot be put in as it stands: {a.change.why}.</p>
	{:else if a.change?.state === 'taken'}<p class="why">The text already reads as it taken.</p>{/if}
	{#if where?.copy}<p class="why" data-testid="suggestion-on-copy">It is on the agent's copy, and comes in with the copy.</p>{/if}
	{#if said?.at === a.id}<Said text={said.text} refused={said.refused} testid="suggestion-said" />{/if}
{/snippet}

<main class="page scrollbar-shown" class:review-page={!opened} data-testid="proposed">
	<ReviewHeading title="Proposed to you" />
	{#if opened}<p class="back"><a href={here} data-testid="proposed-back">‹ Everything proposed</a></p>{/if}
	{#if adoption}
		{@const copy = adoption.copy}
		{#key copy}<ContributionReview contribution={adoption} onanswer={(a) => (answer = a && { ...a, from: copy })} />{/key}
	{:else if pull}
		{#key pull.commit}<IncomingPull incoming={pull} label={pullLabel(m)} writable={!!served['sync-incorporate']} onanswer={(a) => (answer = a && { ...a, from: 'pull' })} />{/key}
	{:else if queue}
		<ProposalQueue />
	{:else}
		{#if answer && answer.from !== showing}<div class="answer"><Said text={answer.text} refused={answer.refused} testid="proposed-answer" /></div>{/if}
		{#if !cards.length && !weighing.length}
			{#if said?.at === '*'}<Said text={said.text} refused={said.refused} testid="proposed-bar-said" />{/if}
			<Empty text="Nobody has proposed anything." testid="proposed-none" />
		{:else}
			<ActionBar said={said?.at === '*' ? said.text : ''} refused={said?.refused} testid="proposed-bar">
				{#snippet lead()}
					<span data-testid="proposed-summary">{cards.length} to decide · {weighing.length} to consider</span>
				{/snippet}
				{#snippet actions()}
					{#if undo}<button type="button" class="btn small" disabled={!!busy} data-testid="proposed-undo" onclick={() => void takeBack()}>Undo</button>{/if}
				{/snippet}
			</ActionBar>
			<p class="lead">What agents and collaborators propose. A copy or a pull is reviewed in one pass. A suggestion you take is written into its file, a version of the document kept first; a citation you take is kept as a reference note, and nothing is written into the text.</p>
			{#if decides && why}<p class="lead" data-testid="proposed-no-session"><NoSession /></p>{/if}
			<ul class="plain cards" data-testid="proposed-cards">
				{#each cards as c (c.kind + c.id)}
					<li class="card" data-testid="proposed-card" data-kind={c.kind} data-id={c.id}>
						{#if c.kind === 'pull'}
							<div class="line">
								<span class="tag">a pull</span>
								<span class="name">{c.label}</span>
								<span class="acts"><a class="btn small primary" href="{here}?pull" data-testid="proposed-open">Review the pull</a></span>
							</div>
							<p class="why">{count(c.pull.changes.length, 'change', 'changes')}, taken whole.</p>
							{@render chips(c.pull.changes.map((x) => ({ name: x.name ?? x.key, bad: x.conflict })))}
						{:else if c.kind === 'copy'}
							{@const items = itemsOf(m, c.copy)}
							<div class="line">
								<span class="tag">an agent's copy</span>
								<span class="name">{file(c.copy.copy)}</span>
								<span class="of">into {file(c.copy.source)}</span>
								<span class="acts"><a class="btn small primary" href="{here}?copy={encodeURIComponent(c.copy.copy)}" data-testid="proposed-open">Review the copy</a></span>
							</div>
							<p class="why" data-testid="proposed-tally">{copySays(tally(c.copy, items))}.</p>
							{#if c.copy.issues.length}<p class="why" data-testid="proposed-issue">{c.copy.issues[0]}</p>{/if}
							{@render chips(items.map((i) => ({ name: i.name, bad: !i.can })))}
							{#if c.suggestions.length}
								<details class="on-copy" data-testid="proposed-on-copy">
									<summary>{count(c.suggestions.length, 'suggestion', 'suggestions')} on it, which come in with the copy</summary>
									<ul class="plain">
										{#each c.suggestions as a (a.id)}<li class="folded" data-testid="suggestion" data-id={a.id}>{@render textSuggestion(a)}</li>{/each}
									</ul>
								</details>
							{/if}
						{:else if c.kind === 'suggestion'}
							<div data-testid="suggestion" data-id={c.id}>{@render textSuggestion(c.annotation)}</div>
						{:else if c.kind === 'citation'}
							{@const a = c.annotation}
							<div class="line">
								<span class="tag">a citation</span>
								<a class="name" href={placeUrl(m, a.target.key, a.id, a.in)} data-testid="citation-open">{name(a)}</a>
								<span class="of">· {writerOf(m, a)}</span>
								<span class="acts">
									{#if served['library-cite']}
										<button type="button" class="btn small primary" disabled={!!busy || !!why} title={why || 'Keep it as a reference note; nothing is written into the text'} data-testid="proposed-take" onclick={() => void act(a, 'library-cite', { decision: 'accept' }, `Kept the citation on ${name(a)} as a reference note`)}>{busy === a.id ? 'Taking…' : 'Take it'}</button>
										<button type="button" class="btn small" disabled={!!busy || !!why} title={why || undefined} data-testid="proposed-leave" onclick={() => void act(a, 'library-cite', { decision: 'reject' }, `Left the citation on ${name(a)}`)}>Leave it</button>
									{/if}
								</span>
							</div>
							<Prose html={a.body_html} />
							{#if a.payload}<p class="why" data-testid="citation-work">Proposes citing: {a.payload}</p>{/if}
							{#if said?.at === a.id}<Said text={said.text} refused={said.refused} testid="suggestion-said" />{/if}
						{:else}
							{@const ref = m.references[c.citekey]}
							<div class="line">
								<span class="tag">results from a paper</span>
								<a class="name" href={workUrl(c.citekey)}>{surnames(ref?.bib.author) || c.citekey}, {bibText(ref?.bib.title) || c.citekey}</a>
								<span class="acts"><a class="btn small primary" href="{here}?work={encodeURIComponent(c.citekey)}#queue" data-testid="proposed-open">Check them</a></span>
							</div>
							<p class="why">{count(c.count, 'result an agent proposes', 'results an agent proposes')}, each to compare with the paper.</p>
						{/if}
					</li>
				{/each}
			</ul>
			{#if weighing.length}
				<details class="consider" open data-testid="proposed-consider">
					<summary>To consider <span class="n">{weighing.length}</span> <span class="of">each is prose, with nothing to take in: resolve it once you have acted on it, or dismiss it</span></summary>
					<ul class="plain">
						{#each weighing as a (a.id)}
							<li class="folded" data-testid="suggestion" data-id={a.id}>
								<div class="line">
									{@render suggestionHead(a)}
									<span class="acts">
										{#if served.resolve}
											<button type="button" class="btn small" disabled={!!busy || !!why} title={why || 'You have acted on it'} data-testid="suggestion-resolve" onclick={() => void act(a, 'resolve', {}, `Resolved the suggestion on ${name(a)}`)}>Resolve</button>
										{/if}
										{#if served.discard}
											<button type="button" class="btn small quiet" disabled={!!busy || !!why} title={why || 'It should not have been raised'} data-testid="suggestion-dismiss" onclick={() => ((asking = a.id), (reason = ''), (said = null))}>Dismiss…</button>
										{/if}
									</span>
								</div>
								{#if a.quote}<q class="quoted" data-testid="suggestion-quote"><TexProse text={a.quote} /></q>{/if}
								<Prose html={a.body_html} />
								{@render dismissing(a)}
								{#if said?.at === a.id}<Said text={said.text} refused={said.refused} testid="suggestion-said" />{/if}
							</li>
						{/each}
					</ul>
				</details>
			{/if}
		{/if}
	{/if}
</main>

<style>
	.back {
		margin: -8px 2px var(--gap);
		font-size: 13px;
	}
	.answer {
		margin-bottom: var(--gap);
	}
	.lead {
		margin: 0 0 var(--gap);
		font-size: 13px;
		color: var(--ink-soft);
	}
	.card {
		margin: 0 0 var(--gap-tight);
		padding: 12px 14px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--review-paper);
	}
	.line {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 8px;
	}
	.name {
		font-size: 14px;
		overflow-wrap: anywhere;
	}
	.of,
	.n {
		color: var(--ink-soft);
		font-size: 12.5px;
		font-weight: 400;
	}
	.tag {
		padding: 1px 8px;
		border-radius: 999px;
		background: var(--leaf);
		color: var(--ink-soft);
		font-size: 11.5px;
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
	.chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		margin-top: 8px;
		font-size: 12px;
	}
	.chip {
		padding: 1px 9px;
		border: 1px solid var(--rule);
		border-radius: 999px;
		color: var(--ink-soft);
		overflow-wrap: anywhere;
	}
	.chip.bad {
		border-color: var(--state-stale);
		color: var(--state-stale);
	}
	.more {
		color: var(--ink-faint);
	}
	.on-copy {
		margin-top: 8px;
		font-size: 13px;
	}
	.consider {
		margin-top: var(--gap);
		padding: 10px 14px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		font-size: 13px;
	}
	.folded {
		margin: 10px 0 0;
		padding-top: 10px;
		border-top: 1px solid var(--rule);
		font-size: 14px;
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
