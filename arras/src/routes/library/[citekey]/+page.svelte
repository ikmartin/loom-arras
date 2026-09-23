<script lang="ts">
	// A cited work: the paper, the digest read off it, and what the corpus knows about it.
	//
	// **The paper opens first, always.** A work in the Library is a document a reader came to read, and the digest is
	// a derived index of it — useful, and never the thing you meant when you clicked the title. The three tabs are the
	// first thing on the page, and everything that is *about* the work rather than *of* it stands behind **Info**, so
	// the reading surface is the paper and nothing else.
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
	import PdfTools from '$lib/pdf/PdfTools.svelte';
	import { PdfView } from '$lib/pdf/view.svelte';
	import Beside from '$lib/split/Beside.svelte';
	import BesideToggle from '$lib/split/BesideToggle.svelte';
	import Tabs from '$lib/split/Tabs.svelte';
	import ReadingActs from '$lib/shell/ReadingActs.svelte';
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
	/** The page to open at: whatever the URL names, else the first. A paper always opens somewhere. */
	const reading = $derived(Number(page.url.searchParams.get('page') ?? '') || 1);
	const readable = $derived(!ref?.unreadable && !!ref?.artifacts?.pdf);
	// What a discussion beside this work is about: its digest nodes and its proposals, which is everything on the page.
	const about = $derived([...(ref?.work ? [ref.work] : []), ...(ref?.digest?.nodes ?? []), ...(ref?.proposed?.nodes ?? [])]);
	// The place the URL points at, in the one locator syntax `cited:` links share (plan 0.13 item 6).
	const locator = $derived<WorkLink | null>(ref?.work ? readKeys({ id: ref.work }, page.url.search.slice(1)) : null);

	let tab = $state<'paper' | 'digest' | 'info'>('paper');
	/** The reader's view of the paper, shared by the rail's controls and the renderer below them. */
	const pdf = new PdfView();

	const tabs = $derived([
		{ id: 'paper', label: 'Paper' },
		...(ref?.digest || proposals.length ? [{ id: 'digest', label: 'Digest' }] : []),
		{ id: 'info', label: 'Info' }
	]);

	let asBibtex = $state(false);
	let copied = $state('');

	/** The entry as BibTeX, rebuilt from the fields the manifest carries: what you paste into a `.bib`. */
	const bibtex = $derived.by(() => {
		if (!ref) return '';
		const type = String(ref.bib.ENTRYTYPE ?? 'article');
		const body = bibRows.map(([k, v]) => `  ${k} = {${v}}`).join(',\n');
		return `@${type}{${citekey},\n${body}\n}`;
	});

	async function copyBibtex(): Promise<void> {
		try {
			await navigator.clipboard.writeText(bibtex);
			copied = 'copied';
		} catch {
			copied = 'could not copy — select the text instead';
		}
		setTimeout(() => (copied = ''), 2500);
	}

	/** The bibliography entry as rows, in the order a reader scans: who, when, where, then the rest. */
	const FIRST = ['author', 'title', 'year', 'journal', 'booktitle', 'publisher', 'volume', 'number', 'pages', 'doi', 'eprint', 'url'];
	const bibRows = $derived(
		Object.entries(ref?.bib ?? {})
			.filter(([k, v]) => k !== 'ENTRYTYPE' && k !== 'ID' && String(v).trim() !== '')
			.sort((a, b) => {
				const ia = FIRST.indexOf(a[0]);
				const ib = FIRST.indexOf(b[0]);
				return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a[0].localeCompare(b[0]);
			})
	);
</script>

<main class="page" class:reading={tab === 'paper'}>
	{#if !ref}
		<h1>Unknown reference</h1>
	{:else}
		<!-- One line for the whole of the top, in the rail the layout draws: which text you are reading, the controls for reading it, and the split. The tabs come first because which of the three you are in is the only question that has to be answered before anything else; the paper's own title is on the paper, and Info has the rest. -->
		<ReadingActs>
			{#snippet lead()}<Tabs {tabs} bind:value={tab} />{/snippet}
			{#snippet acts()}
				{#if tab === 'paper' && readable}<PdfTools view={pdf} />{/if}
				<BesideToggle open={!!page.url.searchParams.get('page')} />
			{/snippet}
		</ReadingActs>
		<Beside keys={about} label="this work" control={false} open={!!page.url.searchParams.get('page')}>
			{#if tab === 'paper'}
				{#if readable}
					<div class="reader" data-testid="reader">
						<Reading {citekey} {ref} page={reading} {locator} view={pdf} toolbar={false} />
					</div>
				{:else if ref.unreadable}
					<p class="muted" data-testid="unreadable">
						Declared unreadable: {ref.unreadable.why} — {ref.unreadable.who}. Nothing here can be checked against a page.
					</p>
				{:else}
					<p class="muted" data-testid="no-copy">No copy of this paper is filed here. <WorkLinks {ref} /></p>
				{/if}
			{:else if tab === 'digest'}
				<div class="prose">
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
					{/if}
				</div>
			{:else}
				<div class="prose info" data-testid="work-info">
					<h1><Tex text={bibText(ref.bib.title) || citekey} /></h1>
					<p class="links"><code>{citekey}</code> <WorkLinks {ref} /></p>

					<!-- Read as a list, taken as BibTeX. The list is for the eye; the entry is what goes into a `.bib`, and
					     retyping it from a rendered list is exactly the thing a reader should never have to do. -->
					<p class="bibtools">
						<button type="button" class:on={asBibtex} data-testid="bibtex-toggle" onclick={() => (asBibtex = !asBibtex)}>
							{asBibtex ? 'list' : 'bibtex'}
						</button>
						{#if asBibtex}<button type="button" data-testid="bibtex-copy" onclick={copyBibtex}>copy</button>{/if}
						{#if copied}<span class="said" role="status">{copied}</span>{/if}
					</p>
					{#if asBibtex}
						<pre class="bibtex" data-testid="bibtex">{bibtex}</pre>
					{:else}
						<dl class="bib" data-testid="bib-list">
							{#each bibRows as [field, value] (field)}
								<dt>{field}</dt>
								<dd><Tex text={bibText(value)} /></dd>
							{/each}
						</dl>
					{/if}

					{#if ref.digest}
						<p class="muted">Digest from {ref.digest.source} ({ref.digest.method}).</p>
					{/if}
					{#if ref.version_mismatch}
						<p class="problem">The digest's source and the bibliography name different versions of this work.</p>
					{/if}
					{#if ref.unreadable}
						<p class="muted">Declared unreadable: {ref.unreadable.why} — {ref.unreadable.who}.</p>
					{/if}

					<LinkList heading="Links touching this paper" forKeys={Object.keys(ref.results ?? {})} />
				</div>
			{/if}
		</Beside>
	{/if}
</main>

<style>
	/* Reading the paper is a full-height job: the column fills the pane and scrolls inside itself, so the page behind
	   it never scrolls and the reader never runs out of paper at the bottom of a screen. */
	.page.reading {
		display: flex;
		flex-direction: column;
		height: calc(100vh - var(--above, 0px));
		overflow: hidden;
		padding: 0;
		max-width: none;
	}
	.reader {
		flex: 1 1 auto;
		min-height: 0;
	}
	/* Inside the split the content pane is a scroll container, so the paper grew to its full length. The held column is given the pane's height and scrolls inside the reader instead, which is where a paper should scroll. */
	.page.reading :global(.held) {
		height: 100%;
		min-height: 0;
		display: flex;
		flex-direction: column;
		padding: 0;
	}
	.prose {
		padding: var(--gap) var(--gap-wide);
		min-width: 0;
	}
	.info h1 {
		margin-top: 0;
	}
	.links {
		display: flex;
		align-items: center;
		gap: var(--gap-tight);
		margin-top: 0;
	}
	/* the entry as a reader reads it: the field names quiet and aligned, the values in the body face */
	.bib {
		display: grid;
		grid-template-columns: max-content minmax(0, 1fr);
		gap: 2px var(--gap);
		margin: var(--gap) 0;
		font-size: 0.9rem;
	}
	.bib dt {
		font-family: var(--sans);
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		padding-top: 0.25em;
	}
	.bib dd {
		margin: 0;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.bibtools {
		display: flex;
		align-items: center;
		gap: var(--gap-hair);
		margin: var(--gap) 0 var(--gap-hair);
	}
	.bibtools button {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		background: none;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 1px 7px;
		cursor: pointer;
	}
	.bibtools button:hover {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
	.bibtools button.on {
		background: var(--link-wash);
		border-color: var(--link);
		color: var(--link);
	}
	.said {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
	.bibtex {
		font-family: var(--mono);
		font-size: 12px;
		line-height: 1.5;
		white-space: pre;
		overflow-x: auto;
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: var(--gap-tight);
		margin: 0 0 var(--gap);
		user-select: text;
	}
	.fold {
		font: inherit;
		color: inherit;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
	}
</style>
