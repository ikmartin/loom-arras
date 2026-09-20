<script lang="ts">
	// The digest view (plan 0.12 §9.1): what this corpus knows about other people's papers, and the place proposals are met.
	//
	// Not `/review`. That page is the corpus's own keys and their acceptance states, and its columns -- state, cause, since, blocks, reached-by -- have nothing in common with what a proposal needs, which is both texts side by side, the anchor, the page and the run that proposed it. DR-172 spent its effort separating the literature out of `/review`; putting proposals there would remix exactly what was separated.
	//
	// The backlog is this page with its filter set to `proposed` (§9.3): one route, one data path, two densities. Browse mode for meeting a proposal where it stands, list mode for working through a pile.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import { bibText } from '$lib/works';
	import { digestUrl } from '$lib/nav';
	import { setQuery } from '$lib/query';

	const m = $derived(store.manifest!);
	const SHOWS = ['all', 'proposed', 'digested', 'unread'] as const;
	const q = (name: string) => page.url.searchParams.get(name) ?? '';
	const filter = $derived((SHOWS as readonly string[]).includes(q('show')) ? q('show') : 'all');

	interface Row {
		citekey: string;
		title: string;
		cited: number;
		verified: number;
		proposed: number;
		nodes: number;
	}

	const rows = $derived<Row[]>(
		Object.values(m.references)
			.map((r) => {
				const results = Object.values(r.results ?? {});
				return {
					citekey: r.citekey,
					title: bibText(r.bib.title as string) || r.citekey,
					cited: r.cited_by.length,
					verified: results.filter((x) => x.state === 'verified').length,
					proposed: results.filter((x) => x.state === 'proposed').length,
					nodes: r.digest?.nodes.length ?? 0
				};
			})
			// what the corpus leans on most, first: the works nothing cites are not worth anyone's attention yet
			.sort((a, b) => b.proposed - a.proposed || b.cited - a.cited || a.citekey.localeCompare(b.citekey))
	);

	const shown = $derived(
		rows.filter((r) =>
			filter === 'proposed'
				? r.proposed > 0
				: filter === 'digested'
					? r.nodes > 0
					: filter === 'unread'
						? r.nodes === 0 && r.proposed === 0
						: true
		)
	);
	const totals = $derived({
		proposed: rows.reduce((n, r) => n + r.proposed, 0),
		verified: rows.reduce((n, r) => n + r.verified, 0),
		works: rows.filter((r) => r.nodes > 0).length
	});
	const show = (v: string) => void setQuery(page.url, 'show', filter === v ? 'all' : v, 'all');
</script>

<PagePanel>
	<h2>Digest</h2>
	<p class="muted">
		The papers this corpus cites, and what has been read of them. A <strong>proposal</strong> is a statement an agent read off a page and rendered; it sits in a file nothing inputs until you have looked at both texts and said the copy is faithful.
	</p>
	<p class="filters">
		<button class="count" class:on={filter === 'proposed'} aria-pressed={filter === 'proposed'} onclick={() => show('proposed')} data-testid="show-proposed">{totals.proposed} proposed</button>
		<span class="sep">·</span>
		<button class="count" class:on={filter === 'digested'} aria-pressed={filter === 'digested'} onclick={() => show('digested')} data-testid="show-digested">{totals.works} digested</button>
		<span class="sep">·</span>
		<button class="count" class:on={filter === 'unread'} aria-pressed={filter === 'unread'} onclick={() => show('unread')} data-testid="show-unread">{rows.length - totals.works} not read</button>
	</p>
</PagePanel>

<main class="page">
	<table class="list" data-testid="digest-works">
		<thead>
			<tr><th>work</th><th>cited</th><th>results</th><th>proposed</th></tr>
		</thead>
		<tbody>
			{#each shown as r (r.citekey)}
				<tr>
					<td class="work">
						<a class="title" href={digestUrl(r.citekey)}><Tex text={r.title} /></a>
						<span class="byline"><code>{r.citekey}</code></span>
					</td>
					<td class="num">{r.cited || '—'}</td>
					<td class="num">{r.nodes || '—'}</td>
					<td class="num">
						{#if r.proposed}<a class="pending" href={digestUrl(r.citekey)} data-testid="pending-{r.citekey}">{r.proposed}</a>{:else}—{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if !shown.length}
		<p class="muted">Nothing here. {#if filter !== 'all'}<button class="as-link" onclick={() => show(filter)}>Show every work</button>{/if}</p>
	{/if}
</main>

<style>
	.filters {
		margin: var(--gap-tight) 0 0;
		font-size: 0.9em;
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
	.sep {
		color: var(--rule-strong);
		margin: 0 0.4em;
	}
	td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.pending {
		font-weight: 600;
	}
	.byline {
		display: block;
		font-size: 0.85em;
		color: var(--ink-faint);
	}
	a.title {
		font-weight: 500;
	}
</style>
