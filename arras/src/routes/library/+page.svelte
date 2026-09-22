<script lang="ts">
	// The Library (DR-206): every work this corpus cites, as a **whole document** rather than as loose digest nodes.
	//
	// It replaces `/digest` and `/references`, which listed the same papers twice under two names. That was an artefact
	// of building the digest index before a work was a thing one could open: once the viewer renders the PDF, the work
	// is the object and its digest is one of the things it has. So one row per work, carrying what both pages carried —
	// what cites it, what has been read of it, what waits on the author, and how to reach it outside the corpus.
	//
	// The backlog is this page with its filter set to `proposed`: one route, one data path, two densities (plan 0.12
	// §9.3). Browse mode for meeting a proposal where it stands, list mode for working through a pile.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import { bibText } from '$lib/works';
	import { keyUrl, workUrl } from '$lib/nav';
	import { setQuery } from '$lib/query';

	const m = $derived(store.manifest!);
	const SHOWS = ['all', 'proposed', 'digested', 'unread', 'held'] as const;
	const q = (name: string) => page.url.searchParams.get(name) ?? '';
	const filter = $derived((SHOWS as readonly string[]).includes(q('show')) ? q('show') : 'all');

	interface Row {
		citekey: string;
		title: string;
		cited: string[];
		verified: number;
		proposed: number;
		nodes: number;
		held: boolean;
		unreadable: string;
	}

	const rows = $derived<Row[]>(
		Object.values(m.references)
			.map((r) => {
				const results = Object.values(r.results ?? {});
				// a digest's own results cite the paper they come from, which says nothing about who uses it
				const cited = r.cited_by.filter((k) => m.nodes[m.keys[k]?.node ?? k]?.digest !== r.citekey);
				return {
					citekey: r.citekey,
					title: bibText(r.bib.title as string) || r.citekey,
					cited,
					verified: results.filter((x) => x.state === 'verified').length,
					proposed: results.filter((x) => x.state === 'proposed').length,
					nodes: r.digest?.nodes.length ?? 0,
					held: !!r.artifacts?.pdf || !!r.artifacts?.source,
					unreadable: r.unreadable?.why ?? ''
				};
			})
			// what the corpus leans on most, first: the works nothing cites are not worth anyone's attention yet
			.sort((a, b) => b.proposed - a.proposed || b.cited.length - a.cited.length || a.citekey.localeCompare(b.citekey))
	);

	const shown = $derived(
		rows.filter((r) =>
			filter === 'proposed'
				? r.proposed > 0
				: filter === 'digested'
					? r.nodes > 0
					: filter === 'unread'
						? r.nodes === 0 && r.proposed === 0
						: filter === 'held'
							? r.held
							: true
		)
	);
	const totals = $derived({
		proposed: rows.reduce((n, r) => n + r.proposed, 0),
		works: rows.filter((r) => r.nodes > 0).length,
		held: rows.filter((r) => r.held).length
	});
	const show = (v: string) => void setQuery(page.url, 'show', filter === v ? 'all' : v, 'all');
	const SHOWN = 6;
	let expanded = $state(new Set<string>());
	const toggle = (ck: string) => {
		const next = new Set(expanded);
		if (next.has(ck)) next.delete(ck);
		else next.add(ck);
		expanded = next;
	};
</script>

<PagePanel label="Library">
	<h2>Library</h2>
	<p class="muted">
		The papers this corpus cites, as documents. A <strong>proposal</strong> is a statement an agent read off a page
		and rendered; it sits in a file nothing inputs until you have looked at both texts and said the copy is faithful.
	</p>
	<p class="filters">
		<button class="count" class:on={filter === 'proposed'} aria-pressed={filter === 'proposed'} onclick={() => show('proposed')} data-testid="show-proposed">{totals.proposed} proposed</button>
		<span class="sep">·</span>
		<button class="count" class:on={filter === 'digested'} aria-pressed={filter === 'digested'} onclick={() => show('digested')} data-testid="show-digested">{totals.works} digested</button>
		<span class="sep">·</span>
		<button class="count" class:on={filter === 'held'} aria-pressed={filter === 'held'} onclick={() => show('held')} data-testid="show-held">{totals.held} on this machine</button>
		<span class="sep">·</span>
		<button class="count" class:on={filter === 'unread'} aria-pressed={filter === 'unread'} onclick={() => show('unread')} data-testid="show-unread">{rows.length - totals.works} not read</button>
	</p>
</PagePanel>

<main class="page">
	<h1>Library</h1>
	<table class="list" data-testid="library-works">
		<thead>
			<tr><th>work</th><th>links</th><th>cited by</th><th>results</th><th>proposed</th></tr>
		</thead>
		<tbody>
			{#each shown as r (r.citekey)}
				{@const ref = m.references[r.citekey]}
				<tr>
					<td class="work">
						<a class="title" href={workUrl(r.citekey)}><Tex text={r.title} /></a>
						<span class="byline">
							<code>{r.citekey}</code>{#if ref.bib.author} · <Tex text={bibText(ref.bib.author)} />{/if}
							{#if r.unreadable}<span class="held" data-testid="unreadable-{r.citekey}">· declared unreadable</span>
							{:else if r.held}<span class="held">· on this machine</span>{/if}
						</span>
					</td>
					<td><WorkLinks {ref} /></td>
					<td class="cited">
						{#each r.cited.slice(0, expanded.has(r.citekey) ? undefined : SHOWN) as k, i (k)}{#if i}, {/if}<a href={keyUrl(m, k)}>{k}</a>{:else}<span class="muted">—</span>{/each}
						{#if r.cited.length > SHOWN}
							<button class="as-link more" onclick={() => toggle(r.citekey)}>{expanded.has(r.citekey) ? 'fewer' : `+${r.cited.length - SHOWN}`}</button>
						{/if}
					</td>
					<td class="num">{r.nodes || '—'}</td>
					<td class="num">
						{#if r.proposed}<a class="pending" href={workUrl(r.citekey)} data-testid="pending-{r.citekey}">{r.proposed}</a>{:else}—{/if}
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
	.cited {
		font-size: 11px;
		overflow-wrap: anywhere;
	}
	.more {
		margin-left: var(--gap-hair);
		font-size: 10px;
	}
	td.num {
		text-align: right;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.pending {
		font-weight: 600;
	}
</style>
