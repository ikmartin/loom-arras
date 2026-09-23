<script lang="ts">
	// The Library's ledger (DR-206; plan 0.13.3, View 4): every work this corpus cites, with what the author needs to know to work on it — whether a copy is filed, how much has been read off it, how much of that the text leans on, what awaits their judgment and what is unanswered on it. One question per column.
	//
	// **The list of works has one home, and it is the side panel** (P2): this page is a working table, not a second list to navigate by, so it registers no panel of its own and the panel keeps its Library section beside it. Its filters are its own, in its header.
	//
	// The backlog is this page filtered to `proposed` (DR-206). The filters are the three that answer "which of these need me": a column already says which are filed or digested, and a filter that restated it would be one fact said twice.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import { bibText } from '$lib/works';
	import { workUrl } from '$lib/nav';
	import { setQuery } from '$lib/query';
	import { reachedExternal } from '$lib/reached';
	import { ledgerRow, needsWork } from '$lib/library';

	const m = $derived(store.manifest!);
	const SHOWS = [
		{ v: 'all', label: 'all' },
		{ v: 'needs-work', label: 'needs work' },
		{ v: 'proposed', label: 'proposed' }
	] as const;
	const asked = $derived(page.url.searchParams.get('show') ?? '');
	const filter = $derived(SHOWS.some((s) => s.v === asked) ? asked : 'all');

	const rows = $derived.by(() => {
		const reached = reachedExternal(m);
		return Object.values(m.references)
			.map((r) => ledgerRow(m, r, reached))
			// what wants the author first, then by key: a ledger is read for what is owed
			.sort((a, b) => Number(needsWork(b)) - Number(needsWork(a)) || a.citekey.localeCompare(b.citekey));
	});
	const shown = $derived(rows.filter((r) => (filter === 'needs-work' ? needsWork(r) : filter === 'proposed' ? r.unvouched > 0 : true)));
	const count = (v: string) => (v === 'needs-work' ? rows.filter(needsWork).length : v === 'proposed' ? rows.filter((r) => r.unvouched > 0).length : rows.length);
	const show = (v: string) => void setQuery(page.url, 'show', v, 'all');
	const n = (x: number) => x || '—';
</script>

<main class="page">
	<header class="head">
		<h1>Library</h1>
		<p class="filters" role="group" aria-label="which works">
			{#each SHOWS as s (s.v)}
				<button class="count" class:on={filter === s.v} aria-pressed={filter === s.v} onclick={() => show(s.v)} data-testid="show-{s.v}">{s.label} <span class="n">{count(s.v)}</span></button>
			{/each}
		</p>
	</header>
	<table class="list" data-testid="library-works">
		<thead>
			<tr>
				<th>work</th>
				<th title="a copy of the paper is filed here">filed</th>
				<th class="num" title="results read off it">digest</th>
				<th class="num" title="of those, what this corpus leans on">used here</th>
				<th class="num" title="statements nobody has vouched for">unvouched</th>
				<th class="num" title="notes and findings still awaiting an answer">open</th>
				<th>links</th>
			</tr>
		</thead>
		<tbody>
			{#each shown as r (r.citekey)}
				{@const ref = m.references[r.citekey]}
				<tr data-testid="ledger-{r.citekey}">
					<td class="work">
						<a class="title" href={workUrl(r.citekey)}><Tex text={r.title} /></a>
						<span class="byline">
							<code>{r.citekey}</code>{#if ref.bib.author} · <Tex text={bibText(ref.bib.author)} />{/if}
							{#if r.unreadable}<span class="held" data-testid="unreadable-{r.citekey}">· declared unreadable</span>{/if}
						</span>
					</td>
					<td><span class="dot" class:filed={r.filed} role="img" aria-label={r.filed ? 'filed here' : 'not filed here'}></span></td>
					<td class="num" data-testid="digest-{r.citekey}">{n(r.digest)}</td>
					<td class="num" data-testid="used-{r.citekey}">{n(r.used)}</td>
					<td class="num">
						{#if r.unvouched}<a class="pending" href={workUrl(r.citekey) + '?view=digest'} data-testid="pending-{r.citekey}">{r.unvouched}</a>{:else}—{/if}
					</td>
					<td class="num" data-testid="open-{r.citekey}">{n(r.open)}</td>
					<td><WorkLinks {ref} /></td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if !shown.length}
		<p class="muted">Nothing here. {#if filter !== 'all'}<button class="as-link" onclick={() => show('all')}>Show every work</button>{/if}</p>
	{/if}
</main>

<style>
	/* The page's own header, on one line: the table is the first screen (P1). */
	.head {
		display: flex;
		align-items: baseline;
		gap: var(--gap-wide);
		margin-bottom: var(--gap);
	}
	.head h1 {
		margin: 0;
	}
	.filters {
		display: flex;
		gap: var(--gap);
		margin: 0;
		font-family: var(--sans);
		font-size: 12px;
	}
	.n {
		color: var(--ink-faint);
		font-variant-numeric: tabular-nums;
	}
	button.count {
		background: none;
		border: none;
		padding: 0;
		font: inherit;
		color: var(--ink-soft);
		cursor: pointer;
	}
	button.count.on {
		color: var(--ink);
		font-weight: 600;
	}
	.work {
		max-width: 26rem;
	}
	a.title {
		display: block;
		font-family: var(--body-face);
		font-size: 13px;
		line-height: 1.4;
		font-weight: 500;
	}
	.byline {
		display: block;
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		line-height: 1.5;
	}
	.byline code {
		font-size: 9px;
		background: none;
		padding: 0;
	}
	.held {
		margin-left: 0.2em;
	}
	th.num,
	td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.pending {
		font-weight: 600;
	}
	/* Filled where a copy is filed, hollow where none is: the one thing a click on the work cannot be guessed to give. */
	.dot {
		display: inline-block;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		box-shadow: inset 0 0 0 1.5px var(--ink-faint);
	}
	.dot.filed {
		background: var(--state-accepted);
		box-shadow: none;
	}
</style>
