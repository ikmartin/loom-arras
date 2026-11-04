<script lang="ts">
	// One review of an agent's copy (plan 0.25.2): every change it makes, named as the person reads it and grouped by section, decided one at a time in a bar that never moves. Take it and Leave it are saved at once and step to the next change to decide; Apply writes what was taken into the paper in one press, keeping the paper as it was first and accepting the blocks the person marked as checked. Whatever loom answers, done or refused, is said in the bar beside the controls that asked.
	import ActionBar from './ActionBar.svelte';
	import Said from './Said.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { AdoptionReview, IncorporationMathReview, IncorporationOutcome } from '$lib/manifest/types';
	import { masterUrl, placeUrl } from '$lib/nav';
	import { can, write } from '$lib/write';
	import { onMount } from 'svelte';
	import { acceptFor, decision, itemsOf, stateOf, takeAll, tally, type Decision, type Item } from './contribution';

	let { contribution: c, onanswer }: { contribution: AdoptionReview; onanswer?: (a: { text: string; refused: boolean } | null) => void } = $props();
	// the last answer, said in the bar and handed to the page, which keeps saying it once this contribution is gone
	let answer = $state<{ text: string; refused: boolean } | null>(null);
	function say(a: { text: string; refused: boolean } | null): void {
		answer = a;
		onanswer?.(a);
	}

	const m = $derived(store.manifest!);
	const items = $derived(itemsOf(m, c));
	const n = $derived(tally(c, items));
	const reviewer = $derived(m.reviewer?.name ?? '');
	let writable = $state(false);
	let active = $state('');
	let filter = $state('');
	let busy = $state('');
	let checked = $state<string[]>([]);
	onMount(() => {
		void can('adopt-decision').then((yes) => (writable = yes));
	});
	const acts = $derived(writable && !!reviewer && !c.issues.length);
	const file = (path: string) => path.split('/').pop()?.replace(/\.tex$/, '') ?? path;
	const index = $derived(Math.max(0, items.findIndex((i) => i.key === active)));
	const current = $derived<Item | undefined>(items[index]);
	const standing = $derived(current ? stateOf(c, current) : 'undecided');
	const shown = $derived(filter.trim() ? items.filter((i) => `${i.name} ${i.detail} ${i.section}`.toLowerCase().includes(filter.trim().toLowerCase())) : items);
	// the list's sections in the order they first come, each heading every change under it
	const groups = $derived.by(() => {
		const out: { section: string; items: Item[] }[] = [];
		for (const i of shown) {
			const at = out.find((g) => g.section === i.section);
			if (at) at.items.push(i);
			else out.push({ section: i.section, items: [i] });
		}
		return out;
	});
	const SAYS: Record<string, string> = { taken: 'taken', left: 'left out', undecided: 'to decide' };
	const says = (i: Item) => (i.can ? SAYS[stateOf(c, i)] : "can't be taken") + (i.change?.class === 'merged' ? ' · merged' : '');

	function go(to: number): void {
		const next = items[Math.min(items.length - 1, Math.max(0, to))];
		if (next) active = next.key;
	}
	/** The next change after `from` still to decide, else `from` itself. */
	function onward(from: string): void {
		const at = items.findIndex((i) => i.key === from);
		const next = [...items.slice(at + 1), ...items.slice(0, at)].find((i) => i.can && stateOf(c, i) === 'undecided');
		if (next) active = next.key;
	}
	async function save(d: Decision, from?: string): Promise<void> {
		busy = 'decide';
		const done = await write('adopt-decision', { copy: c.copy, fingerprint: c.fingerprint, revision: c.choices?.revision ?? 0, ...d });
		if (done.ok) {
			store.setAdoption(c.copy, c.fingerprint, done.result as unknown as AdoptionReview['choices']);
			say(null);
			if (from) onward(from);
		} else {
			say({ text: done.error?.message ?? 'Loom did not save that choice.', refused: true });
			await store.refresh();
		}
		busy = '';
	}
	function choose(item: Item, take: boolean): void {
		if (!take) checked = checked.filter((k) => k !== item.key);
		void save(decision(c, item, take), item.key);
	}
	function toggle(key: string, on: boolean): void {
		checked = on ? [...new Set([...checked, key])] : checked.filter((k) => k !== key);
	}

	/** Apply in one press: loom prepares what was taken, and writes it when nothing stands in the way; a refusal is said in the bar, one reason a line. */
	async function apply(): Promise<void> {
		busy = 'apply';
		say(null);
		const prepared = await write('adopt-preview', { copy: c.copy, fingerprint: c.fingerprint });
		if (!prepared.ok) {
			say({ text: prepared.error?.message ?? 'Loom could not prepare these changes.', refused: true });
			busy = '';
			return;
		}
		const p = prepared.result as unknown as { token: string; review: IncorporationMathReview; adoption_base?: { mapping?: Record<string, string> } };
		const accept = acceptFor(p.review, checked.filter((k) => c.choices.keys.includes(k)), p.adoption_base?.mapping ?? {});
		const taken = n.taken;
		const done = await write('adopt-finish', { copy: c.copy, token: p.token, review_token: p.review.token, accept });
		if (done.ok) {
			const o = done.result as unknown as IncorporationOutcome;
			const into = file(c.source);
			// marked as checked yet not accepted: loom says why when recording failed, and otherwise it is because what they rest on was not accepted
			const dropped = checked.filter((k) => c.choices.keys.includes(k)).length - accept.length;
			const why = o.acceptance_error ? ` ${o.acceptance_error}` : dropped > 0 ? ` ${dropped} marked as checked wait too, since what they rest on was not accepted.` : '';
			say({
				text: `Took ${taken} ${taken === 1 ? 'change' : 'changes'} into ${into}: ${o.accepted?.length ?? 0} accepted, ${o.pending?.length ?? 0} wait in Needs review. ${into} as it was is kept as a version.${why}`,
				refused: false
			});
			checked = [];
			await store.refresh();
		} else say({ text: done.error?.message ?? 'Loom did not write these changes.', refused: true });
		busy = '';
	}
	async function refreshCopy(): Promise<void> {
		busy = 'refresh';
		const done = await write('adopt-refresh', { copy: c.copy });
		say({ text: done.ok ? 'The copy now has your latest text wherever you changed it alone; a clash stays until it is reconciled.' : (done.error?.message ?? 'Loom did not refresh the copy.'), refused: !done.ok });
		if (done.ok) await store.refresh();
		busy = '';
	}
</script>

<section class="contribution" data-testid="contribution" data-copy={c.copy}>
	<ActionBar testid="contribution-bar" said={answer?.text ?? ''} refused={answer?.refused}>
		{#snippet lead()}
			<b>From {file(c.copy)}</b> into {file(c.source)} · {n.taken} taken · {n.left} left · {n.undecided} to decide{#if n.clash}{' · '}{n.clash} can't be taken{/if}
		{/snippet}
		{#snippet actions()}
			{#if acts}
				<button class="btn" disabled={!!busy || n.undecided + n.left === 0} onclick={() => save(takeAll(items))} data-testid="take-all">Take all</button>
				<button class="btn primary" disabled={!!busy || !n.taken} onclick={apply} data-testid="apply">{busy === 'apply' ? 'Applying…' : `Apply ${n.taken} ${n.taken === 1 ? 'change' : 'changes'}`}</button>
			{/if}
		{/snippet}
		{#snippet below()}
			<div class="step">
				<button class="btn small quiet" disabled={index <= 0} onclick={() => go(index - 1)} aria-label="Previous change" data-testid="prev-change">‹</button>
				<span class="at" data-testid="change-at">{items.length ? index + 1 : 0} of {items.length}</span>
				<button class="btn small quiet" disabled={index >= items.length - 1} onclick={() => go(index + 1)} aria-label="Next change" data-testid="next-change">›</button>
				<span class="now">{current?.name ?? ''}</span>
				{#if acts && current}
					{#if current.can}
						<button class="btn small" class:primary={standing === 'taken'} aria-pressed={standing === 'taken'} disabled={!!busy} onclick={() => choose(current, true)} data-testid="take-it">{standing === 'taken' ? 'Taken' : 'Take it'}</button>
						<button class="btn small" aria-pressed={standing === 'left'} disabled={!!busy} onclick={() => choose(current, false)} data-testid="leave-it">{standing === 'left' ? 'Left out' : 'Leave it'}</button>
						{#if current.kind === 'result'}
							<label class="accept" title="Records your acceptance of this block's mathematics as it is written in, when you apply"><input type="checkbox" checked={checked.includes(current.key)} disabled={standing !== 'taken' || !!busy} onchange={(e) => toggle(current.key, e.currentTarget.checked)} data-testid="accept-checked" /> accept as checked</label>
						{/if}
					{:else}
						<span class="why" data-testid="cannot-take">{current.why}</span>
						<button class="btn small" disabled={!!busy} onclick={refreshCopy} data-testid="refresh-copy">Refresh the copy</button>
					{/if}
				{/if}
			</div>
		{/snippet}
	</ActionBar>
	<p class="lead">An agent's copy of {file(c.source)}. Take or leave each change; Apply writes the ones you took into {file(c.source)}, keeping it as it was first. <a href={masterUrl(c.copy)}>Read the copy</a></p>
	{#each c.issues as issue, i (i)}<Said text={issue} refused />{/each}
	{#if writable && !reviewer}<p class="muted">Choose your reviewer name in Settings to take changes.</p>{/if}
	<div class="workspace">
		<aside aria-label="The copy's changes">
			<input class="find" type="search" placeholder="find a change" aria-label="Find a change" bind:value={filter} data-testid="change-filter" />
			{#each groups as g (g.section + g.items[0].key)}
				{#if g.section}<p class="group">{g.section}</p>{/if}
				{#each g.items as it (it.key)}
					<button class="row" class:active={it.key === current?.key} onclick={() => (active = it.key)} data-testid="change-row" data-key={it.key} data-state={it.can ? stateOf(c, it) : 'clash'}>
						<span class="name">{it.name}</span><small>{says(it)}</small>
					</button>
				{/each}
			{:else}
				<p class="muted">No change matches.</p>
			{/each}
		</aside>
		<div class="change" data-testid="change-shown">
			{#if current}
				<h2>{current.name}</h2>
				{#if current.detail}<p class="detail">{current.detail}</p>{/if}
				{#if current.kind === 'result' && current.change}
					{@const ch = current.change}
					{#if ch.class === 'merged'}<p class="note" data-testid="merged-note">You both changed it, and the edits fall apart line by line: what would be written holds both.</p>{/if}
					{#if ch.class === 'removed'}<p class="note">The copy removes it from {file(c.source)}.</p>{/if}
					{#if ch.class === 'separate-result'}<p class="note">It belongs to another document, so it is taken as a result of its own.</p>{/if}
					{#if !ch.math_changed && ch.class !== 'new' && ch.class !== 'removed'}<p class="note">This changes its source, not its mathematics.</p>{/if}
					<div class="pair">
						<div><h4>Yours</h4>{#if ch.local}<Fragment path={ch.local} />{:else}<p class="muted">New in this copy.</p>{/if}</div>
						<div><h4>{ch.class === 'merged' ? 'With both edits' : "The copy's"}</h4>{#if ch.incoming}<Fragment path={ch.incoming} macroSet={ch.incoming_macros} isolatedMacros />{:else}<p class="muted">{ch.class === 'removed' ? 'Removed.' : ch.proposed}</p>{/if}</div>
					</div>
					{#if ch.documents.length > 1}<p class="muted">This result is shared: it changes in {ch.documents.filter((d) => d !== c.source).map(file).join(', ')} too.</p>{/if}
					{#if ch.affected.length}<p class="muted">May bear on: {#each ch.affected as a, i (a.key)}{i ? ', ' : ''}<a href={placeUrl(m, a.key)}>{a.key}</a>{/each}</p>{/if}
				{:else if current.kind === 'prose'}
					{#if c.document_comparison}
						{@const pair = c.document_comparison}
						<div class="pair">
							<div><h4>Yours</h4>{#if pair.local}<Fragment path={pair.local} />{:else}<pre>{pair.current}</pre>{/if}</div>
							<div><h4>The copy's</h4>{#if pair.incoming}<Fragment path={pair.incoming} macroSet={pair.incoming_macros} isolatedMacros />{:else}<pre>{pair.proposed}</pre>{/if}</div>
						</div>
					{/if}
					<details><summary>Source of the prose and ordering</summary><pre>{c.document_diff}</pre></details>
				{:else if current.kind === 'preamble'}
					<div class="pair">
						<div><h4>Yours</h4><pre>{c.preamble_current}</pre></div>
						<div><h4>The copy's</h4><pre>{c.preamble_proposed}</pre></div>
					</div>
				{/if}
			{/if}
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
	.accept {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		color: var(--ink-soft);
	}
	.why {
		flex-basis: 100%;
		color: var(--state-stale);
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
	.find {
		width: 100%;
		box-sizing: border-box;
		margin-bottom: var(--gap-tight);
		font: inherit;
		font-size: 12.5px;
		padding: 4px 8px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		background: var(--sheet);
	}
	.group {
		margin: var(--gap-tight) 0 2px;
		font-size: 11px;
		color: var(--ink-faint);
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
	.row[data-state='taken'] small {
		color: var(--state-accepted);
	}
	.row[data-state='clash'] small {
		color: var(--state-stale);
	}
	.change {
		min-width: 0;
	}
	.change h2 {
		font: 400 21px/1.3 Georgia, serif;
		margin: 0;
	}
	.detail,
	.note {
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
