<script lang="ts">
	// A cited work (plan 0.13.3 K1–K5): the paper, the digest read off it, and what the corpus knows about it.
	//
	// **The paper opens first, always.** A work in the Library is a document a reader came to read, and the digest is a derived index of it — useful, and never the thing you meant when you clicked the title. The three views are the first thing in the rail, and everything that is *about* the work rather than *of* it stands behind **Info**, so the reading surface is the paper and nothing else, full bleed in its pane.
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
	import type { WorkLink } from '$lib/worklink';
	import type { Item } from '../item';
	import { workState } from '../state.svelte';
	import { workViews } from '../views';

	let { item }: { item: Item } = $props();
	import { slotsFor } from '$lib/fragments/slots';

	const m = $derived(store.manifest!);
	const slots = slotsFor(() => m);
	const citekey = $derived(item.id);
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
	/** The page to open at: whatever the item's place names, else the first. A paper always opens somewhere. */
	const reading = $derived(item.place?.page || 1);
	const readable = $derived(!ref?.unreadable && !!ref?.artifacts?.pdf);
	// The place the item points at, in the one locator syntax `cited:` links share (plan 0.13 item 6).
	const locator = $derived<WorkLink | null>(ref?.work ? { id: ref.work, ...(item.place ?? {}) } : null);

	/** Which of the three views is open: the item's, and the paper when it names none or one this work lacks. */
	const tab = $derived(workViews(m, item.id).some((v) => v.id === item.view) ? item.view! : 'paper');
	/** The reader's view of the paper, shared with the rail's controls, which draw it once for the current item. */
	const pdf = $derived(workState(item).pdf);

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

{#if !ref}
	<div class="page item"><h1>Unknown reference</h1></div>
{:else}
	<div class="page item work" class:reading={tab === 'paper'}>
		{#if tab === 'paper'}
			{#if readable}
				<div class="reader" data-testid="reader">
					<Reading {citekey} {ref} page={reading} {locator} view={pdf} />
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
						<!-- the heading and its count alone: each proposal carries its own `proposed` flag, and what a proposal is is the book's to say (10.2.3), not the view's -->
						<h2>Proposed <span class="muted">{proposals.length}</span></h2>
						{#each proposals as p (p.id)}
							<ProposalBox id={p.id} record={p.record} {citekey} />
						{/each}
					</section>
				{/if}
				{#if ref.digest}
					<Fragment path={ref.digest.fragment} macroSet={citekey} comments={slots} authoring={false} anchor="" />
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
	</div>
{/if}

<style>
	/* Reading the paper is a full-height job, and full bleed (K4): the column fills the pane and scrolls inside itself, so the pane never scrolls and the reader never runs out of paper at the bottom of a screen. */
	.page.reading {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
		padding: 0;
		max-width: none;
	}
	.reader {
		flex: 1 1 auto;
		min-height: 0;
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
