<script lang="ts">
	// The left column: the quilt's name, the fold and Settings at its head; two tabs choosing the primary view, **Docs** (reading and writing) and **Review** (the quilt's management); beneath them that view's column; and a footer, in both views, holding the problems chip and the session footer. Folded, it is a narrow rail keeping what must stay in reach: unfold, search, the chip and the session's dot.
	//
	// **Docs** holds search, then a page's own panel where it registers one (the graph's filters, the problems' filters), else the documents — the working drafts, the agent's documents under their directory's name with the closed ones folded beneath, the Library, the landmarks — and then the Outline of the document in the focused pane, a section of its own. A result is read in the document that holds it (V7), so the column lists no nodes.
	import Contents from './Contents.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { canonUrl, masterUrl, workUrl } from '$lib/nav';
	import { bibText } from '$lib/works';
	import SessionFooter from '$lib/sessions/SessionFooter.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { onMount } from 'svelte';
	import { can } from '$lib/write';
	import Settings from './Settings.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { route } from '$lib/paths';
	import type { ShellProps } from './props';

	let { label, primary, docsHref, indexes, masters, canon, currentDoc, onDocument, contents, currentSection, counts, search, children, rail, panel, panelLabel }: ShellProps = $props();

	// The problems chip answers whether anything is wrong, so it takes the colour of the worst thing it counts and says the count.
	const tally = $derived([counts.errors ? `${counts.errors} error${counts.errors === 1 ? '' : 's'}` : '', counts.warnings ? `${counts.warnings} warning${counts.warnings === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ') || 'no problems');
	const problemCount = $derived(counts.errors + counts.warnings);
	// The Library in the column: a work is one thing a reader opens, so the column lists them. A row carries the work's title and a dot for whether a copy is filed — the one thing a click cannot be guessed to give — and no counts, which the ledger governs.
	const works = $derived(
		Object.values(store.manifest?.references ?? {}).sort((a, b) => (bibText(a.bib.title) || a.citekey).localeCompare(bibText(b.bib.title) || b.citekey))
	);
	let readOnly = $state(false);
	onMount(() => { void can('review-decision').then((yes) => readOnly = !yes); });
	const reviewPerspective = $derived(store.manifest?.reviewer?.name
		? `Review status for ${store.manifest.reviewer.name}`
		: Object.values(store.manifest?.keys ?? {}).some((key) => key.acceptance) ? 'Review perspective unspecified' : '');
	let workFilter = $state('');
	const library = $derived.by(() => {
		const q = workFilter.trim().toLowerCase();
		return q ? works.filter((r) => `${r.citekey} ${bibText(r.bib.title)} ${bibText(r.bib.author ?? '')}`.toLowerCase().includes(q)) : works;
	});

	// **On a narrow window the column goes first** (plan 0.13 §7): below 1200px the workspace needs the width, so the column shows folded whatever the reader's stored choice, and the fold opens it for this visit without rewriting that choice. A window widened again shows the stored choice.
	const SQUEEZED = 1200;
	let windowWidth = $state(typeof window === 'undefined' ? SQUEEZED : window.innerWidth);
	let peek = $state<boolean | null>(null);
	const squeezed = $derived(windowWidth < SQUEEZED);
	const shown = $derived(squeezed ? (peek ?? false) : prefs.panel);
	$effect(() => {
		if (!squeezed) peek = null;
	});
	function fold(): void {
		if (squeezed) peek = !shown;
		else prefs.panel = !prefs.panel;
	}

	// Documents: the drafts being worked on and the landmarks recorded, as a list rather than a dropdown, because a dropdown shows one name at a time and cannot say which draft is conflicted or which landmark a step wrote. Newest landmark first: the one a reader is most likely to want.
	const landmarks = $derived([...canon].reverse());
	const own = $derived(masters.filter((m) => !m.closed && !m.context_only && m.directory !== 'drafting-ai'));
	const withAgent = $derived(masters.filter((m) => !m.closed && !m.context_only && m.directory === 'drafting-ai'));
	const closed = $derived(masters.filter((m) => m.closed));
	// The file name, not the typeset title: two drafts of one paper share a title and differ only in their path, which is what the author types and what the read view's URL names them by.
	const filename = (path: string) => path.split('/').pop() || path;
	const outline = $derived(onDocument && contents.length > 0);

	let libraryOpen = $state(true);
	// Open at rest (plan 0.13.3 S2): where am I in this is the question asked most often while reading, and should not cost a click.
	let outlineOpen = $state(true);
</script>

<svelte:window bind:innerWidth={windowWidth} />

{#snippet chip(iconOnly: boolean)}
	<a
		href={route('/problems')}
		class="problems"
		class:errors={counts.errors > 0}
		class:warnings={!counts.errors && counts.warnings > 0}
		class:icon-only={iconOnly}
		aria-label="problems: {tally}"
		title="problems: {tally}"
		data-testid="problems-chip"><Icon name="problems" size={14} />{#if !iconOnly}<span>{problemCount ? problemCount : 'no problems'}</span>{/if}</a
	>
{/snippet}

<div class="shell-c">
	<div class="panel" class:away={!shown} data-testid="column">
		{#if !shown}
			<!-- folded: what must stay in reach, one above the other -->
			<button class="fold" title="Show the column" aria-label="Show the column" aria-expanded="false" data-testid="panel-fold" onclick={fold}>»</button>
			<button class="rail-search" onclick={search} aria-label="Search" title="search"><Icon name="search" /></button>
			<div class="rail-foot">
				{@render chip(true)}
				<SessionFooter compact />
			</div>
		{:else}
			<div class="head">
				<a href={route('/')} class="name" data-testid="quilt-name">{label}</a>
				<Settings {indexes} />
				<button class="fold" title="Hide the column" aria-label="Hide the column" aria-expanded="true" data-testid="panel-fold" onclick={fold}>«</button>
			</div>
			<nav class="primary" aria-label="Primary views">
				<!-- back to Docs returns to the workspace's address, which names the place a link last sent a tab to; each pane puts the reader back where they were, so neither scrolling nor focus is let go to that place first -->
				<a
					href={docsHref || route('/')}
					class:on={primary === 'docs'}
					aria-current={primary === 'docs' ? 'page' : undefined}
					data-sveltekit-noscroll=""
					data-sveltekit-keepfocus=""
					data-testid="primary-docs">Docs</a
				>
				<!-- a corpus that declares no review has no Review; one that says nothing either way keeps it -->
				{#if store.manifest?.publishes?.review !== false}<a href={route('/review')} class:on={primary === 'review'} aria-current={primary === 'review' ? 'page' : undefined} data-testid="primary-review">Review</a>{/if}
			</nav>
			<!-- Whose review a read-only view shows is said once, under the quilt it belongs to, and never above the document. -->
			{#if readOnly && reviewPerspective}<p class="review-perspective">{reviewPerspective}</p>{/if}
			<div class="sections rail-scroll">
				{#if primary === 'docs'}
					<button class="search" onclick={search} data-testid="column-search"><Icon name="search" size={13} /><span>Search</span><kbd>⌘K</kbd></button>
				{/if}
				{#if panel}
					<p class="rail-label">{panelLabel}</p>
					<div class="page-panel rail-scroll">{@render panel()}</div>
				{:else if primary === 'docs'}
					{#snippet doc(path: string, href: string, step?: string)}
						{@const here = onDocument && path === currentDoc}
						<li>
							<a {href} class:here aria-current={here ? 'page' : undefined}>
								{filename(path)}{#if step}<span class="aside"> @{Number(step)}</span>{/if}
							</a>
						</li>
					{/snippet}
					{#if own.length}
						<p class="rail-label">Drafts</p>
						<ul class="plain docs" data-testid="docs-drafts">
							{#each own as m (m.path)}{@render doc(m.path, masterUrl(m.path))}{/each}
						</ul>
					{/if}
					{#if withAgent.length || closed.length}
						<!-- the documents the person and an agent both edit, under the directory they live in, as the person's editor shows it -->
						<p class="rail-label dir">{(withAgent[0] ?? closed[0]).path.split('/').slice(0, -1).join('/')}/</p>
						{#if withAgent.length}
							<ul class="plain docs" data-testid="docs-drafts-ai">
								{#each withAgent as m (m.path)}{@render doc(m.path, masterUrl(m.path))}{/each}
							</ul>
						{/if}
						{#if closed.length}
							<details class="closed" data-testid="docs-closed">
								<summary>Closed agent documents</summary>
								<ul class="plain docs">
									{#each closed as m (m.path)}{@render doc(m.path, masterUrl(m.path))}{/each}
								</ul>
							</details>
						{/if}
					{/if}
					{#if works.length}
						<p class="rail-label">
							<button class="shelf" aria-expanded={libraryOpen} data-testid="library-toggle" onclick={() => (libraryOpen = !libraryOpen)}>
								{libraryOpen ? '▾' : '▸'} Library <span class="aside">({works.length})</span>
							</button>
						</p>
						{#if libraryOpen}
							{#if works.length > 6}<input class="filter" type="search" placeholder="narrow by title, author or key" aria-label="Narrow the works" bind:value={workFilter} data-testid="library-filter" />{/if}
							<ul class="plain library" data-testid="library-list">
								{#each library as r (r.citekey)}
									<li>
										<a href={workUrl(r.citekey)}
											><span class="dot" class:filed={!!r.artifacts?.pdf} role="img" aria-label={r.artifacts?.pdf ? 'filed here' : 'not filed here'}></span>{bibText(r.bib.title) || r.citekey}</a
										>
										{#if r.unreadable}<span class="aside">unreadable</span>{/if}
									</li>
								{:else}
									<li class="aside">nothing matches</li>
								{/each}
								<li><a href={route('/library')} data-testid="ledger-link">ledger</a></li>
							</ul>
						{/if}
					{/if}
					{#if landmarks.length}
						<p class="rail-label">Landmarks</p>
						<ul class="plain docs" data-testid="docs-canon">
							{#each landmarks as c (c.path)}{@render doc(c.path, canonUrl(c.path), c.step)}{/each}
						</ul>
					{/if}
					{#if outline}
						<!-- the focused pane's document's sections, a section of their own below the documents -->
						<p class="rail-label outline-label">
							<button class="shelf" aria-expanded={outlineOpen} data-testid="contents-toggle" onclick={() => (outlineOpen = !outlineOpen)}>
								{outlineOpen ? '▾' : '▸'} Outline <span class="aside">{filename(currentDoc)}</span>
							</button>
						</p>
						{#if outlineOpen}<div class="outline" data-testid="outline"><Contents entries={contents} masterPath={currentDoc} current={currentSection} /></div>{/if}
					{/if}
				{/if}
			</div>
			<!-- Pinned outside the scroll (S5), in both views: writes land in the selected session whatever is shown, so a reader must never go looking for where their work will go; and whether anything is wrong is answered beside it. -->
			<div class="write-target">
				<div class="chip-row">{@render chip(false)}</div>
				<SessionFooter />
			</div>
		{/if}
	</div>

	<div class="content">
		{@render children()}</div>
	{#if rail}<aside class="right rail-scroll">{@render rail()}</aside>{/if}
</div>

<style>
	.review-perspective { margin: 0 0 var(--gap-tight); font-size: 11.5px; color: var(--ink-soft); overflow-wrap: anywhere; }
	.shell-c {
		display: grid;
		grid-template-columns: var(--rail-left) minmax(0, 1fr) auto;
		min-height: 100vh;
	}
	/* folded, the column is a narrow rail, not a 252px empty gutter */
	.shell-c:has(.panel.away) {
		grid-template-columns: var(--rail-folded) minmax(0, 1fr) auto;
	}
	/* The chip takes the colour of the worst thing it counts, so whether anything is wrong is legible at a glance. */
	.problems {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 11.5px;
		color: var(--ink-faint);
		padding: 2px 6px;
		border-radius: var(--rad-control);
	}
	.problems:hover {
		color: var(--ink);
		background: var(--sheet);
		text-decoration: none;
	}
	.problems.errors {
		color: var(--state-incomplete);
	}
	.problems.warnings {
		color: var(--state-stale);
	}
	.problems.icon-only {
		justify-content: center;
		width: 32px;
		height: 26px;
		padding: 0;
	}
	.chip-row {
		display: flex;
		padding: 0 0 var(--gap-hair);
	}
	.panel {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		padding: var(--gap) 14px;
		position: sticky;
		z-index: 10;
		top: 0;
		height: 100vh;
		display: flex;
		flex-direction: column;
		gap: var(--gap-hair);
		overflow: hidden;
		z-index: 20;
	}
	.sections {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		gap: var(--gap-hair);
	}
	/* **A section keeps its own height; the column scrolls.** Flex children shrink by default, and a shrunk box whose
	   overflow is visible paints its content over whatever follows it — which is what garbled Contents into Library the
	   moment Nodes was expanded and the panel ran past the window. The page panel is the exception: it is the whole
	   panel on a route that brings one, so it takes the space. */
	.sections > *:not(.page-panel) {
		flex: 0 0 auto;
	}
	/* folded: unfold, search, and at the foot the chip and the session's dot, one above the other */
	.panel.away {
		align-items: center;
		padding-left: 4px;
		padding-right: 4px;
		gap: 12px;
	}
	.rail-search {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 26px;
		color: var(--ink-faint);
		background: none;
		border: none;
		border-radius: var(--rad-control);
		cursor: pointer;
	}
	.rail-search:hover {
		color: var(--ink);
		background: var(--sheet);
	}
	.rail-foot {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		width: 100%;
	}
	.rail-foot :global(.footer) {
		margin: 0 -4px calc(-1 * var(--gap));
		align-self: stretch;
	}
	/* the two primary views: one line of two words, the current one underlined */
	.primary {
		display: flex;
		gap: 16px;
		margin: 0 0 var(--gap-tight);
		border-bottom: 1px solid var(--rule);
		font-size: 12.5px;
	}
	.primary a {
		padding: 4px 0 6px;
		color: var(--ink-soft);
		margin-bottom: -1px;
	}
	.primary a:hover {
		color: var(--ink);
		text-decoration: none;
	}
	.primary a.on {
		color: var(--ink);
		box-shadow: inset 0 -2px 0 var(--accent);
	}
	/* search looks like a field and is a button: it opens the palette, which is the one search */
	.search {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		box-sizing: border-box;
		margin: 0 0 var(--gap-tight);
		padding: 3px 6px;
		font: inherit;
		font-size: 11.5px;
		color: var(--ink-faint);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 4px;
		cursor: pointer;
		text-align: left;
	}
	.search span {
		flex: 1;
	}
	.search kbd {
		font: inherit;
		font-size: 10px;
	}
	.search:hover {
		color: var(--ink-soft);
	}
	.filter {
		width: 100%;
		box-sizing: border-box;
		font: inherit;
		font-size: 11px;
		padding: 2px 5px;
		margin: 0 0 var(--gap-hair);
		border: 1px solid var(--rule);
		border-radius: 3px;
		background: var(--sheet);
		color: var(--ink);
	}
	.fold {
		font: inherit;
		font-size: 11px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 2px 3px;
		cursor: pointer;
	}
	.fold:hover {
		color: var(--ink);
	}
	.page-panel {
		flex: 1;
		min-height: 0;
	}
	.head .name {
		font-size: 13px;
		color: var(--ink);
		font-weight: 500;
	}
	.head .name:hover {
		text-decoration: none;
	}
	.head {
		display: flex;
		align-items: center;
		gap: var(--gap-tight);
		margin-bottom: var(--gap-hair);
	}
	.head .name {
		margin-right: auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	ul.plain {
		list-style: none;
		margin: 0 0 var(--gap-tight);
		padding: 0;
	}
	ul.plain a {
		display: block;
		font-size: 11px;
		color: var(--ink-soft);
		padding: 1px 6px;
		border-radius: var(--rad-pill);
	}
	ul.plain a:hover {
		color: var(--ink);
		text-decoration: none;
	}
	.write-target {
		flex: none;
	}
	.content {
		min-width: 0;
	}
	aside.right {
		width: var(--rail-right);
		border-left: 1px solid var(--rule);
		padding: var(--gap);
		position: sticky;
		top: 0;
		max-height: 100vh;
	}
	.shelf {
		font: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
		text-transform: inherit;
		letter-spacing: inherit;
	}
	/* the agent's directory, named as written, not upper-cased */
	.rail-label.dir {
		text-transform: none;
		letter-spacing: 0;
	}
	.closed summary {
		font-size: 10.5px;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-hair) 6px;
		cursor: pointer;
	}
	.outline {
		margin: 0 0 var(--gap-tight) 6px;
	}
	.outline-label .aside {
		text-transform: none;
		letter-spacing: 0;
	}
	/* The document being read carries the same weight as the current section in the contents, because they are the same
	   fact told twice: where you are. */
	.docs a.here {
		color: var(--ink);
		font-weight: 600;
	}
	/* Filled where a copy is filed, hollow where none is. */
	.library .dot {
		display: inline-block;
		flex: none;
		width: 6px;
		height: 6px;
		margin-right: 6px;
		border-radius: 50%;
		vertical-align: 1px;
		box-shadow: inset 0 0 0 1.2px var(--ink-faint);
	}
	.library .dot.filed {
		background: var(--state-accepted);
		box-shadow: none;
	}
	.library .aside,
	.docs .aside {
		margin-left: 0.3em;
		color: var(--ink-faint);
		font-size: 0.9em;
	}
	/* A graph needs room beside its selection; on a narrow screen the selection follows it. */
	@media (max-width: 800px) {
		.shell-c:has(:global(main.graph)) > .panel { grid-row: 1 / span 2; }
		.shell-c:has(:global(main.graph)) > .content { grid-column: 2; grid-row: 1; }
		.shell-c:has(:global(main.graph)) > aside.right { grid-column: 2; grid-row: 2; width: auto; max-height: none; position: static; border-left: 0; border-top: 1px solid var(--rule); }
		.shell-c :global(main.graph) { height: 70vh; min-height: 400px; }
	}
</style>
