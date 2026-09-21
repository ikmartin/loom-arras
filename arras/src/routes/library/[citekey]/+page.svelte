<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { keyUrl, nodeUrl } from '$lib/nav';
	import { reachedExternal } from '$lib/reached';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import { bibText } from '$lib/works';
	import Locator from '$lib/components/Locator.svelte';
	import ProposalBox from '$lib/review/ProposalBox.svelte';
	import LinkList from '$lib/review/LinkList.svelte';
	import Reading from '$lib/pdf/Reading.svelte';
	import { setQuery } from '$lib/query';
	import Beside from '$lib/split/Beside.svelte';
	import Tabs from '$lib/split/Tabs.svelte';
	import { readKeys, type WorkLink } from '$lib/worklink';
	import { slotsFor } from '$lib/fragments/slots';

	const m = $derived(store.manifest!);
	const slots = slotsFor(() => m);
	const citekey = $derived(decodeURIComponent(page.params.citekey ?? ''));
	const ref = $derived(m.references[citekey]);
	const citers = $derived((id: string) => [...new Set(m.edges.filter((e) => e.to === id).map((e) => e.from))]); // one entry per citing key, however many edges
	// A full extraction holds every theorem-like result of the cited paper, of which this corpus usually leans on a
	// handful. The rest is context worth having and not worth reading, so it folds.
	const reached = $derived(reachedExternal(m));
	const used = $derived((ref?.digest?.nodes ?? []).filter((id) => reached.has(id)));
	const rest = $derived((ref?.digest?.nodes ?? []).filter((id) => !reached.has(id)));
	let showAll = $state(false);
	// Proposals are merged into the page they are about rather than queued somewhere else: an author meets one while
	// already thinking about the subject it pertains to, which is when they are best placed to judge it (§5.2).
	const proposals = $derived(
		(ref?.proposed?.nodes ?? [])
			.map((id) => ({ id, record: ref?.results?.[id] }))
			.filter((x): x is { id: string; record: NonNullable<typeof x.record> } => !!x.record)
	);
	// The presence of `page` is what opens the reader (0.13 item 6): no separate route, so a page of a paper is a link
	// into the place the paper is already discussed, and closing it leaves the reader where they were.
	const reading = $derived(Number(page.url.searchParams.get('page') ?? '') || 0);
	// The pages anything is anchored to, in order: what there is to open, and nothing when no result was read off a page.
	const anchored = $derived(
		[...new Set(Object.values(ref?.results ?? {}).map((r) => r.page))].filter((p) => p > 0).sort((a, b) => a - b)
	);
	// What a discussion beside this work is about: its digest nodes and its proposals, which is everything on the page.
	const about = $derived([...(ref?.work ? [ref.work] : []), ...(ref?.digest?.nodes ?? []), ...(ref?.proposed?.nodes ?? [])]);
	// The place the URL points at, in the one locator syntax `cited:` links share (plan 0.13 item 6).
	const locator = $derived<WorkLink | null>(ref?.work ? readKeys({ id: ref.work }, page.url.search.slice(1)) : null);
	// Two texts, one pane: the paper and the digest read off it. Tabs belong to the content pane (§7).
	let tab = $state<'paper' | 'digest'>('paper');
</script>

<main class="page">
	{#if !ref}
		<h1>Unknown reference</h1>
	{:else}
		<Beside keys={about} label="this work" open={!!reading}>
		<h1><Tex text={bibText(ref.bib.title) || citekey} /></h1>
		<p class="muted">
			<code>{citekey}</code>{ref.bib.author ? ` · ${bibText(ref.bib.author)}` : ''}{ref.bib.year ? ` · ${ref.bib.year}` : ''}
			<WorkLinks {ref} />
			{#if ref.digest}· digest from {ref.digest.source} ({ref.digest.method}){/if}
			{#if ref.version_mismatch}<span class="problem"> · version mismatch between the digest's source and the bibliography</span>{/if}
		</p>
		<!-- above the digest, not below it: under a 45-result paper the one link on the page was never seen -->
		<LinkList heading="Links touching this paper" forKeys={Object.keys(ref.results ?? {})} />
		{#if ref.unreadable}
			<p class="muted" data-testid="unreadable">
				Declared unreadable: {ref.unreadable.why} — {ref.unreadable.who}. Nothing here can be checked against a page.
			</p>
		{:else if ref.artifacts?.pdf && anchored.length}
			<p class="pages">
				Read the paper:
				{#each anchored as p (p)}
					<button
						class="page-link"
						class:on={reading === p}
						data-testid="read-page-{p}"
						onclick={() => setQuery(page.url, 'page', reading === p ? '' : String(p))}>page {p}</button
					>
				{/each}
			</p>
		{/if}
		{#if reading}
			<Tabs tabs={[{ id: 'paper', label: 'Paper' }, { id: 'digest', label: 'Digest' }]} bind:value={tab} />
		{/if}
		{#if reading && tab === 'paper'}
			<div class="reader">
				<Reading {citekey} {ref} page={reading} {locator} />
			</div>
		{:else}
		{#if proposals.length}
			<section class="proposals" data-testid="proposals">
				<h2>Proposed — {proposals.length} statement{proposals.length === 1 ? '' : 's'} nobody has vouched for</h2>
				<p class="muted">
					Read off the page by an agent and rendered into LaTeX. Neither the digest nor any bundle contains these:
					until you say a copy is faithful, it cannot be cited or compiled.
				</p>
				{#each proposals as p (p.id)}
					<ProposalBox id={p.id} record={p.record} {citekey} />
				{/each}
			</section>
		{/if}
		{#if ref.digest}
			<Fragment path={ref.digest.fragment} macroSet={citekey} comments={slots} authoring={false} />
			<h2>Results used here</h2>
			{#if used.length}
				<ul>
					{#each used as id (id)}
						<li><a href={nodeUrl(id)}>{id}</a> {#if m.nodes[id]?.locator}(<Locator {ref} locator={m.nodes[id].locator} />){/if}: {#each citers(id) as c, i (c)}{#if i}, {/if}<a href={keyUrl(m, c)}>{c}</a>{:else}<span class="muted">not cited</span>{/each}</li>
					{/each}
				</ul>
			{:else}
				<p class="muted">Nothing here depends on this reference yet.</p>
			{/if}
			{#if rest.length}
				<h2>
					<button class="fold" onclick={() => (showAll = !showAll)} aria-expanded={showAll} data-testid="digest-rest">
						{showAll ? '▾' : '▸'} {rest.length} further result{rest.length === 1 ? '' : 's'} nothing here uses
					</button>
				</h2>
				{#if showAll}
					<ul>
						{#each rest as id (id)}
							<li><a href={nodeUrl(id)}>{id}</a> {#if m.nodes[id]?.locator}(<Locator {ref} locator={m.nodes[id].locator} />){/if}</li>
						{/each}
					</ul>
				{/if}
			{/if}
		{:else if !proposals.length}
			<p>No digest yet. Cited by: {#each ref.cited_by as c, i (c)}{#if i}, {/if}<a href={keyUrl(m, c)}>{c}</a>{:else}<span class="muted">nothing</span>{/each}</p>
		{/if}
		{/if}
		</Beside>
	{/if}
</main>

<style>
	/* the reader fills what the pane leaves it, so the page column scrolls and the page does not */
	.reader {
		height: calc(80vh - 7rem);
		min-height: 320px;
		border: 1px solid var(--rule, #ddd9cf);
	}
	.fold {
		font: inherit;
		color: inherit;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
	}
	.page-link {
		font: inherit;
		font-size: 0.85rem;
		color: inherit;
		background: none;
		border: 1px solid var(--rule, #ddd9cf);
		border-radius: 3px;
		padding: 1px 6px;
		margin-left: 4px;
		cursor: pointer;
	}
	.page-link.on {
		background: var(--annotation-tint, rgb(217 119 87 / 0.18));
	}
</style>
