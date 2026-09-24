<script lang="ts">
	import { onMount } from 'svelte';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	// All is the complete ledger. Needs review is the ordered block queue. Incoming is the exact collaborator pull before it changes local source.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import type { Cause, IncomingChange, Key, UnresolvedReview } from '$lib/manifest/types';
	import Badge from '$lib/components/Badge.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import { reviewFacts, reviewRowBadge, shortDate } from '$lib/badges';
	import { downstream } from '$lib/graph/layout';
	import { anchorId, keyUrl, masterUrl, threadUrl } from '$lib/nav';
	import { reachedExternal } from '$lib/reached';
	import { can, write } from '$lib/write';

	const m = $derived(store.manifest!);
	const SHOWS = ['all', 'needs-review', 'incoming'] as const;
	const q = (name: string) => page.url.searchParams.get(name) ?? '';
	const filter = $derived((SHOWS as readonly string[]).includes(q('show')) ? q('show') : 'all');
	let open = $state('');
	let blocksOpen = $state('');
	let syncWritable = $state(false);
	let syncBusy = $state(false);
	let syncError = $state('');
	let syncResult = $state<{ source_commit: string; sync_commit: string; integrated: string; paths: string[] } | null>(null);
	let reviewWritable = $state(false);
	let activeReview = $state('');
	let reviewHistory = $state<string[]>([]);
	let reviewError = $state('');
	let reviewBusy = $state(false);
	let guidedRoot = $state<HTMLElement | null>(null);
	let guidedMount = $state(0);
	onMount(() => {
		void can('sync-incorporate').then((yes) => (syncWritable = yes));
		void can('review-decision').then((yes) => (reviewWritable = yes));
	});
	const unresolved = $derived(m.unresolved ?? []);
	const needsReview = $derived(unresolved.filter((r) => r.status === 'needs-review'));
	const pendingOk = $derived(unresolved.filter((r) => r.status === 'ok'));
	const attention = $derived(unresolved.filter((r) => r.status === 'requires-attention'));
	const reviewGroups = $derived([
		{ heading: 'Needs review', entries: needsReview },
		{ heading: 'Pending OK', entries: pendingOk },
		{ heading: 'Requires attention', entries: attention }
	]);
	const activeEntry = $derived(unresolved.find((r) => r.key === activeReview));
	const activeComparison = $derived(activeEntry ? m.keys[activeEntry.key]?.acceptance?.causes?.find((cause) => cause.comparison) : null);
	const reviewOrigin = (entry: UnresolvedReview) => entry.cause === 'incoming-pull'
		? entry.local_changed === true ? `Pull ${entry.pull.slice(0, 12)} + local edits` : entry.local_changed == null ? `Pull ${entry.pull.slice(0, 12)} · later edits unverified` : `Incoming pull ${entry.pull.slice(0, 12)}`
		: 'Local change';
	$effect(() => {
		void guidedMount;
		const root = guidedRoot;
		const key = activeEntry?.key;
		if (!root || !key) return;
		const targets = (m.keys[key]?.acceptance?.causes ?? [])
			.filter((cause) => cause.kind === 'dependency-changed' && cause.citation && !cause.via)
			.map((cause) => root.querySelector<HTMLElement>(`#${CSS.escape(cause.citation!)}`))
			.filter((target): target is HTMLElement => !!target);
		for (const target of targets) target.classList.add('review-citation-target');
		const first = root.querySelector<HTMLElement>('.review-citation-target');
		const pane = root.closest<HTMLElement>('.guided-current');
		if (pane) pane.scrollTop = 0;
		if (first && pane) {
			const top = first.getBoundingClientRect().top - pane.getBoundingClientRect().top + pane.scrollTop;
			pane.scrollTop = Math.max(0, top - 16);
		}
		if (pane) {
			const paneTop = pane.getBoundingClientRect().top;
			if (paneTop < 16 || paneTop > window.innerHeight - 100) {
				window.scrollBy({ top: paneTop - 16, behavior: 'auto' });
			}
		}
		// and the citation itself is on screen, not only the box it scrolled to: a box whose top is in view can still hold it below the fold
		first?.scrollIntoView({ block: 'nearest' });
		return () => { for (const target of targets) target.classList.remove('review-citation-target'); };
	});
	async function reviewDecision(entry: UnresolvedReview, status: 'ok' | 'requires-attention') {
		if (reviewBusy) return;
		reviewBusy = true; reviewError = '';
		const next = needsReview.find((r) => r.key !== entry.key)?.key ?? '';
		const answer = await write('review-decision', { key: entry.key, status });
		if (answer.ok) { reviewHistory = [...reviewHistory, entry.key]; activeReview = next; }
		else reviewError = answer.error?.message ?? 'Could not save the decision';
		reviewBusy = false;
	}
	async function finishReview() {
		if (reviewBusy) return;
		reviewBusy = true; reviewError = '';
		const answer = await write('review-finish', {});
		if (!answer.ok) reviewError = answer.error?.message ?? 'Could not finish review';
		reviewBusy = false;
	}
	async function incorporatePull() {
		if (!m.incoming || syncBusy) return;
		syncBusy = true; syncError = '';
		const answer = await write('sync-incorporate', { incoming: m.incoming.commit, base: m.incoming.base });
		if (answer.ok) syncResult = answer.result as unknown as typeof syncResult;
		else syncError = answer.error?.message ?? 'Could not incorporate the pull';
		syncBusy = false;
	}

	// An external node owes no proof and counts as settled as a dependency (7.6.3), so leaving the ones nothing
	// depends on out of the queue removes noise without hiding work. What is left is the handful whose acceptance
	// means something precise: this digest faithfully states what the source says.
	const reached = $derived(reachedExternal(m));
	const keys = $derived(
		Object.values(m.keys).filter((k) => {
			const n = m.nodes[k.node];
			return !n?.external || !!n.reached_by.length || reached.has(k.node);
		})
	);
	const isStale = (k: (typeof keys)[number]) => !!k.acceptance && k.acceptance.fresh === false;
	const missingProof = $derived(new Set(m.diagnostics.filter((d) => d.code === 'loom:missing-proof').flatMap((d) => d.keys)));
	const counts = $derived({
		accepted: keys.filter((k) => k.state === 'accepted').length,
		stale: keys.filter(isStale).length,
		draft: keys.filter((k) => k.state === 'draft').length,
		incomplete: keys.filter((k) => k.state === 'incomplete').length,
		proved: keys.filter((k) => k.kind === 'statement' && m.nodes[k.node]?.derived?.proved).length,
		settled: keys.filter((k) => k.kind === 'statement' && m.nodes[k.node]?.derived?.settled).length,
		missingProof: keys.filter((k) => k.kind === 'statement' && missingProof.has(k.key)).length
	});
	const undigested = $derived(Object.values(m.references).filter((r) => !r.digest && r.cited_by.length).map((r) => r.citekey));
	const rows = $derived(keys);
	// What a gap blocks: everything that rests on the node carrying it. Computed only for rows that mark one, since the walk is per node.
	const blocks = $derived(new Map(rows.filter((k) => k.incomplete.length).map((k) => [k.key, [...downstream(m, k.node)].sort()])));
	// A column nothing in the current rows fills is not drawn, so a filtered table is not mostly empty headings.
	const hasFacts = $derived(rows.some((k) => reviewFacts(k)));
	const hasIncomplete = $derived(rows.some((k) => k.incomplete.length));
	const hasCauses = $derived(rows.some((k) => k.acceptance?.causes?.length || k.previous_key_match));
	const cols = $derived(5 + (hasCauses ? 1 : 0) + (hasFacts ? 1 : 0) + (hasIncomplete ? 2 : 0));

	const records = $derived([...new Set(Object.values(m.annotations).map((a) => a.run ?? a.record))].sort());
	const threads = $derived(Object.values(m.threads));
	const causes = (k: string) => m.keys[k]?.acceptance?.causes ?? [];
	function incomingUrl(change: IncomingChange, dependent?: { key: string; citation: string | null }): string {
		const target = dependent?.key ?? change.key;
		const key = m.keys[target];
		const document = key && m.nodes[key.node]?.reached_by[0];
		if (!document) return keyUrl(m, target);
		const anchor = dependent?.citation || anchorId(target);
		return `${masterUrl(document)}?incoming=${encodeURIComponent(change.key)}#${anchor}`;
	}
	const redundantProofCause = (k: Key, c: Cause) => k.kind === 'proof' && c.kind === 'dependency-changed' && c.id === k.node;
	function causeUrl(k: Key, c: Cause, index: number): string | null {
		if (!c.comparison || c.via) return null;
		const document = m.nodes[k.node]?.reached_by[0];
		if (!document) return null;
		const anchor = c.kind === 'own-text-changed' ? anchorId(k.key) : c.kind === 'dependency-changed' ? c.citation : '';
		if (!anchor) return null;
		return `${masterUrl(document)}?review=${encodeURIComponent(k.key)}&cause=${index}#${anchor}`;
	}

	const LEADS: Record<string, string> = {
		all: 'Every statement and proof in this corpus, with its recorded state and review facts.',
		'needs-review': 'An ordered block queue. OK decisions remain pending until Finish review records their acceptances together.',
		incoming: 'The exact collaborator revision, its changed files, and its potential effects before incorporation.'
	};
</script>

<main class="page">
	<h1>Review <HelpDot label="what the review panel shows" topic="review" /></h1>
	{#if !m.masters.length}
		<NoDrafts what="keys to review" />
	{/if}
	<nav class="review-tabs" aria-label="Review views">
		<a class:active={filter === 'all'} aria-current={filter === 'all' ? 'page' : undefined} href="?show=all">All</a>
		<a class:active={filter === 'needs-review'} aria-current={filter === 'needs-review' ? 'page' : undefined} href="?show=needs-review">Needs Review ({needsReview.length})</a>
		<a class:active={filter === 'incoming'} aria-current={filter === 'incoming' ? 'page' : undefined} href="?show=incoming">Incoming ({m.incoming?.changes.length ?? 0})</a>
	</nav>
	<p class="lead">{LEADS[filter]} {filter === 'all' ? 'Recorded states are read from this corpus’s review history.' : 'When served locally, review actions save private decisions.'}</p>
	<p class="counts" data-testid="review-counts">
		{counts.accepted} accepted <span class="sep">·</span>{counts.stale} stale <span class="sep">·</span>{counts.draft} draft <span class="sep">·</span>{counts.incomplete} incomplete <span class="sep">·</span>{counts.proved} proved <span class="sep">·</span>{counts.settled} settled
	</p>

	{#if filter === 'incoming'}
		{#if m.incoming}
			<p class="faint">{m.incoming.remote}/{m.incoming.branch} · {m.incoming.commit.slice(0, 12)} · first observed {shortDate(m.incoming.observed)} · compared with {m.incoming.base.slice(0, 12)}</p>
			{#each m.incoming.issues ?? [] as issue}<p class="incoming-warning">{issue}</p>{/each}
			<h2>Changed source files</h2>
			<ul>{#each m.incoming.files as file (file.path)}<li>{file.status} · <code>{file.path}</code></li>{/each}</ul>
			{#if syncWritable}
				<section class="incoming-change" data-testid="incoming-incorporation">
					<h2>Incorporate this pull</h2>
					<p>Loom will apply this exact reviewed revision and create two local commits. It will neither push nor accept mathematics.</p>
					<button disabled={syncBusy || !!m.incoming.issues?.length} onclick={incorporatePull}>{syncBusy ? 'Incorporating…' : 'Incorporate pull'}</button>
					{#if syncError}<p class="incoming-warning" role="alert">{syncError}</p>{/if}
				</section>
			{/if}
			{#each m.incoming.changes as change (change.key)}
				<section class="incoming-change" data-testid={`incoming-${change.key}`}>
					<h2>{#if change.local}<a href={incomingUrl(change)}>{change.key}</a>{:else}{change.key}{/if} <span class="faint">{change.kind}</span></h2>
					{#if change.conflict}<p class="incoming-warning">Both the local draft and the pull changed this block. Reconcile it before incorporation.</p>{:else if change.already_local}<p class="faint">This incoming text is already present locally.</p>{/if}
					{#if change.local && change.incoming}
						<div class="incoming-pair"><div><h3>Current local</h3><Fragment path={change.local} /></div><div><h3>Incoming</h3><Fragment path={change.incoming} macroSet={change.incoming_macros} isolatedMacros /></div></div>
					{/if}
					{#if change.affected.length}
						<p>Potentially affected: {#each change.affected as dependent, i (dependent.key)}{#if i}, {/if}<a href={incomingUrl(change, dependent)}>{dependent.key} via {change.key}</a>{/each}</p>
					{/if}
				</section>
			{/each}
			{#if m.incoming.files.length}
				<h2>Source diffs</h2>
				{#each m.incoming.files as file (file.path)}{#if file.diff}<details><summary>{file.path}</summary><pre class="incoming-file-diff">{file.diff}</pre></details>{/if}{/each}
			{/if}
		{:else}
			<p class="faint">No fetched source is waiting for review.</p>
			{#if syncResult}
				<section class="incoming-change" data-testid="incorporation-result">
					<h2>Pull incorporated</h2>
					<p>Source commit <code>{syncResult.source_commit.slice(0, 12)}</code> · sync record commit <code>{syncResult.sync_commit.slice(0, 12)}</code></p>
					<p><a href="?show=needs-review">Review affected blocks</a></p>
				</section>
			{/if}
		{/if}
	{:else if filter === 'needs-review'}
		<p>{needsReview.length} need review · {pendingOk.length} pending OK · {attention.length} require attention</p>
		{#if needsReview.length}<button onclick={() => (activeReview = needsReview[0].key)}>Start review</button>{/if}
		{#if reviewError}<p class="incoming-warning" role="alert">{reviewError}</p>{/if}
		{#if pendingOk.length && reviewWritable}<button disabled={reviewBusy} onclick={finishReview}>Finish review · record {pendingOk.length} acceptances</button>{/if}
		{#if activeEntry}
			<section class="incoming-change" data-testid="guided-review">
				<h2>{activeEntry.key} · {reviewOrigin(activeEntry)}</h2>
				<p><a href={keyUrl(m, activeEntry.key)}>Open in document</a></p>
				<div class="guided-pair">
					<div class="guided-current" class:guided-proof={m.keys[activeEntry.key]?.kind === 'proof'} class:guided-statement={m.keys[activeEntry.key]?.kind === 'statement'}>
						<h3>Current block</h3>
						{#if m.nodes[m.keys[activeEntry.key]?.node]?.fragment}<Fragment path={m.nodes[m.keys[activeEntry.key].node].fragment} onmounted={(root) => { guidedRoot = root; guidedMount += 1; }} />{/if}
					</div>
					{#if activeComparison?.comparison}
						<div class="guided-comparison">
							<h3>{activeComparison.kind === 'own-text-changed' ? 'Last accepted' : `Current dependency ${activeComparison.id ?? ''}`}</h3>
							<Fragment path={activeComparison.kind === 'own-text-changed' ? activeComparison.comparison.accepted : activeComparison.comparison.current} macroSet={activeComparison.kind === 'own-text-changed' ? activeComparison.comparison.accepted_macros : undefined} isolatedMacros={activeComparison.kind === 'own-text-changed'} />
						</div>
					{/if}
				</div>
				{#each causes(activeEntry.key) as c, i}<p>{c.kind === 'own-text-changed' ? 'Text edit' : c.kind === 'dependency-changed' ? `Dependency changed: ${c.id}` : c.kind}{#if causeUrl(m.keys[activeEntry.key], c, i)} · <a href={causeUrl(m.keys[activeEntry.key], c, i)!}>Compare</a>{/if}</p>{/each}
				{#if reviewWritable && activeEntry.status === 'needs-review'}
					<p>{activeEntry.changed_text ? 'OK confirms the revised text and its dependencies.' : 'OK confirms this block in its current dependency context.'}</p>
					<button disabled={reviewBusy} onclick={() => reviewDecision(activeEntry, 'ok')}>OK</button>{' '}
					<button disabled={reviewBusy} onclick={() => reviewDecision(activeEntry, 'requires-attention')}>Requires attention</button>
				{:else if reviewWritable && activeEntry.status === 'requires-attention'}
					<p>This block remains unaccepted. Mark it OK when the concern is resolved.</p>
					<button disabled={reviewBusy} onclick={() => reviewDecision(activeEntry, 'ok')}>Mark OK</button>
				{:else if reviewWritable && activeEntry.status === 'ok'}
					<p>This block is pending acceptance at Finish review.</p>
					<button disabled={reviewBusy} onclick={() => reviewDecision(activeEntry, 'requires-attention')}>Requires attention</button>
				{/if}
				{#if reviewHistory.length}<button onclick={() => { activeReview = reviewHistory[reviewHistory.length - 1]; reviewHistory = reviewHistory.slice(0, -1); }}>Back</button>{/if}
				{#if needsReview.some((r) => r.key !== activeEntry.key)}<button onclick={() => (activeReview = needsReview.find((r) => r.key !== activeEntry.key)?.key ?? '')}>Next</button>{/if}
				<button onclick={() => (activeReview = '')}>Return to Needs review</button>
			</section>
		{/if}
		{#each reviewGroups as group}
			<h2>{group.heading}</h2>
				{#if group.entries.length}<ul>{#each group.entries as entry (entry.key)}<li><button class="as-link" onclick={() => (activeReview = entry.key)}>{entry.key}</button> · {reviewOrigin(entry)}{#if entry.invalidated} · changed since decision{/if}</li>{/each}</ul>{:else}<p class="faint">None.</p>{/if}
		{/each}
	{:else}
	<table class="list">
		<thead>
			<tr>
				<th>key</th><th>state</th><th>basis</th><th>since</th>
				{#if hasCauses}<th>cause</th>{/if}
				{#if hasFacts}<th>review</th>{/if}
				{#if hasIncomplete}<th>incomplete</th><th>blocks</th>{/if}
				<th>reached by</th>
			</tr>
		</thead>
		<tbody>
			{#each rows as k (k.key)}
				<tr id={`review-${anchorId(k.key)}`}>
					<td><a href={keyUrl(m, k.key)}>{k.key}</a></td>
					<td><Badge parts={reviewRowBadge(m, k)} />{#if missingProof.has(k.key)}<div class="faint">missing proof</div>{/if}</td>
					<td>{#if m.nodes[k.node]?.kind === 'environment'}{m.nodes[k.node]?.basis === 'unclassified' ? 'needs classification' : m.nodes[k.node]?.basis}{m.nodes[k.node]?.inline_proof ? ' (inline)' : ''}{#if m.nodes[k.node]?.basis === 'unclassified'}<div class="faint">{m.nodes[k.node]?.basis_reason}</div>{/if}{/if}</td>
					<td class="faint nowrap">{k.acceptance ? shortDate(k.acceptance.date) : ''}</td>
					{#if hasCauses}
						<td>
							{#each causes(k.key) as c, i (i)}
								{@const href = causeUrl(k, c, i)}
								<div>
									{#if c.kind === 'own-text-changed'}
										{#if href}<a {href}>text edit</a>{:else}text edit{/if}
									{:else if c.kind === 'dependency-changed'}
										dependency changed: {#if href}<a {href}>{c.id}</a>{:else}{c.id}{/if}{#if c.via}{' '}via {c.via}{/if}
									{:else}{c.kind}{c.id ? ' ' + c.id : ''}{/if}{c.when ? ` (${shortDate(c.when)})` : ''}
									{#if c.diff && !href && !c.via && !redundantProofCause(k, c)}
										· <button class="as-link" onclick={() => (open = open === k.key ? '' : k.key)} data-testid="expand-{k.key}">{open === k.key ? 'hide details' : 'details'}</button>
									{/if}
								</div>
							{/each}
							{#if k.previous_key_match}<div class="faint">acceptance recorded under {k.previous_key_match}; re-accept to confirm</div>{/if}
						</td>
					{/if}
					{#if hasFacts}<td class="faint">{reviewFacts(k)}</td>{/if}
					{#if hasIncomplete}
						<td>{#each k.incomplete as t, i (i)}<div>{t}</div>{/each}</td>
						<td data-testid="blocks-{k.key}">
							{#if blocks.get(k.key)?.length}
								<button class="as-link" onclick={() => (blocksOpen = blocksOpen === k.key ? '' : k.key)} aria-expanded={blocksOpen === k.key}>{blocks.get(k.key)!.length} {blocks.get(k.key)!.length === 1 ? 'result' : 'results'}</button>
							{:else if k.incomplete.length}
								<span class="faint">nothing</span>
							{/if}
						</td>
					{/if}
					<td class="faint">{m.nodes[k.node]?.reached_by.join(', ') || 'loose'}</td>
				</tr>
				{#if open === k.key}
					<tr class="expansion" data-testid="expansion-{k.key}">
						<td colspan={cols}>
							{#each causes(k.key) as c, i (i)}
								{#if c.diff && !redundantProofCause(k, c)}
									<p class="cause">{c.kind}{c.id ? ' · ' + c.id : ''} — accepted text on the left, current text on the right</p>
									<DiffView path={c.diff} />
								{/if}
							{/each}
						</td>
					</tr>
				{/if}
				{#if blocksOpen === k.key}
					<tr class="expansion">
						<td colspan={cols}>
							<p class="cause">not proved while {k.key} is incomplete</p>
							<p class="blocked">{#each blocks.get(k.key) ?? [] as b, i (b)}{#if i}, {/if}<a href={keyUrl(m, b)}>{b}</a>{/each}</p>
						</td>
					</tr>
				{/if}
			{:else}
				<tr><td colspan={cols} class="faint">Nothing matches.</td></tr>
			{/each}
		</tbody>
	</table>
	{/if}

	{#if undigested.length && filter === 'all'}
		<h2>Undigested citations</h2>
		<p class="faint">{undigested.join(', ')}</p>
	{/if}

	{#if filter === 'all'}
		<h2>Sessions</h2>
		{#if threads.length || records.length}
			<ul class="plain">
				{#each threads as t (t.id)}<li><a href={threadUrl(t.id)}>{t.title}</a> {#if t.discarded}<span class="faint">discarded</span>{/if}</li>{/each}
				{#each records as r (r)}<li><code>{r}</code></li>{/each}
			</ul>
		{:else}
			<p class="faint">None yet.</p>
		{/if}
	{/if}
</main>

<style>
	.review-tabs { display: flex; gap: var(--gap-tight); margin: 0 0 var(--gap); border-bottom: 1px solid var(--rule); }
	.review-tabs a { padding: var(--gap-tight) 0; color: var(--ink-soft); text-decoration: none; border-bottom: 2px solid transparent; }
	.review-tabs a.active { color: var(--ink); border-color: var(--link); }
	.guided-pair :global(.review-citation-target) { background: var(--state-stale-wash); outline: 2px solid var(--state-stale); outline-offset: 2px; }
	.guided-pair { display: grid; grid-template-columns: minmax(0, 3fr) minmax(280px, 2fr); gap: var(--gap-wide); }
	.guided-pair > div { min-width: 0; max-height: 65vh; overflow: auto; }
	.guided-pair h3 { font-size: 0.8rem; }
	.guided-statement :global(details.env-proof) { display: none; }
	.guided-proof :global(.env:not(.env-proof)) { display: none; }
	@media (max-width: 900px) { .guided-pair { grid-template-columns: 1fr; } }
	.incoming-change { border-top: 1px solid var(--rule); padding: var(--gap-wide) 0; }
	.incoming-change h2 { font-size: 1rem; }
	.incoming-warning { color: var(--state-stale); }
	.incoming-pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--gap-wide); }
	.incoming-pair > div { min-width: 0; overflow-x: auto; border: 1px solid var(--rule); padding: var(--gap-tight); }
	.incoming-pair h3 { font-size: 0.85rem; }
	.incoming-pair :global(mark.review-changed) { background: var(--state-stale-wash); color: inherit; }
	.incoming-pair :global(.math.review-changed) { background-color: var(--state-stale-wash); outline: 2px solid var(--state-stale); }
	.incoming-file-diff { max-width: 100%; overflow-x: auto; padding: var(--gap-tight); border: 1px solid var(--rule); }
	@media (max-width: 900px) { .incoming-pair { grid-template-columns: 1fr; } }
	.lead {
		max-width: var(--measure);
		color: var(--ink-soft);
		font-size: 12px;
		line-height: 1.6;
	}
	.counts {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
	}
	.counts .sep {
		margin: 0 4px;
		color: var(--ink-faint);
	}
	.nowrap {
		white-space: nowrap;
	}
	.cause {
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-hair);
	}
	.blocked {
		margin: 0;
		font-size: 12px;
	}
	tr.expansion td {
		background: var(--leaf);
		padding: var(--gap-tight);
	}
</style>
