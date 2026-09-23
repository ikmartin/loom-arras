<script lang="ts">
	// The navigation shell (book 15.2.3): a 44px icon strip of the views this corpus has, search, and at its foot the problems glyph and the settings control, beside a panel holding the page's own panel when it has one and the documents otherwise, with the write target pinned beneath.
	// The strip carries no separate home mark: home is one of the views, and a second control going to the same place is a puzzle, not a shortcut.
	import Contents from './Contents.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { canonUrl, masterUrl, nodeUrl, workUrl } from '$lib/nav';
	import { bibText } from '$lib/works';
	import SessionFooter from '$lib/sessions/SessionFooter.svelte';
	import DevShelf from './DevShelf.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Settings from './Settings.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { route } from '$lib/paths';
	import type { ShellProps } from './props';

	let { label, views, indexes, currentView, masters, canon, currentDoc, onDocument, contents, currentSection, counts, search, children, rail, panel, panelLabel }: ShellProps = $props();

	// The problems view stands at the strip's foot as a warning glyph (plan 0.13.3 S9): it answers whether anything is wrong, so it carries the counts and takes their colour.
	const problems = $derived(views.find((v) => v.id === 'problems'));
	const tally = $derived([counts.errors ? `${counts.errors} error${counts.errors === 1 ? '' : 's'}` : '', counts.warnings ? `${counts.warnings} warning${counts.warnings === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ') || 'no problems');
	// The Library in the panel: a work is one thing a reader opens, so the panel lists them rather than their nodes.
	const works = $derived(Object.values(store.manifest?.references ?? {}));
	const library = $derived(works.slice(0, 6));
	const more = $derived(works.length > 6 ? works.length : 0);
	// Nodes (plan 0.13 §7): the corpus's own statements, by id, narrowed by what is typed. Folded by default -- a
	// corpus of a hundred results would otherwise be the panel -- and never the digests' nodes, which the Library
	// lists as works.
	const statements = $derived(
		Object.values(store.manifest?.nodes ?? {})
			.filter((n) => n.kind === 'environment' && !n.external)
			.sort((a, b) => a.id.localeCompare(b.id))
	);
	let nodeFilter = $state('');
	let nodesOpen = $state(false);
	const NODES_SHOWN = 30;
	const matching = $derived.by(() => {
		const q = nodeFilter.trim().toLowerCase();
		return q ? statements.filter((n) => `${n.id} ${n.taxon} ${n.title ?? ''}`.toLowerCase().includes(q)) : statements;
	});

	// Documents: the drafts being worked on and the landmarks recorded, as a list rather than a dropdown, because a
	// dropdown shows one name at a time and cannot say which draft is conflicted or which landmark a step wrote.
	// Newest landmark first: the one a reader is most likely to want.
	const landmarks = $derived([...canon].reverse());
	const docCount = $derived(masters.length + canon.length);
	// The file name, not the typeset title: two drafts of one paper share a title and differ only in their path, which
	// is what the author types and what `--master` and the read view's URL name them by.
	const filename = (path: string) => path.split('/').pop() || path;

	let docsOpen = $state(true);
	// Open at rest (plan 0.13.3 S2): where am I in this is the question asked most often while reading, and should not cost a click.
	let contentsOpen = $state(true);
	let libraryOpen = $state(true);
</script>

<div class="shell-c">
	<nav class="strip" aria-label="Views">
		<ul>
			{#each views.filter((v) => v.id !== 'problems') as v (v.id)}
				<li>
					<a
						href={v.href}
						aria-label={v.label}
						title={v.label}
						class:current={currentView === v.id}
						aria-current={currentView === v.id ? 'page' : undefined}
						data-testid="view-{v.id}"><Icon name={v.icon} /></a
					>
				</li>
			{/each}
			<li><button onclick={search} aria-label="Search" title="search"><Icon name="search" /></button></li>
			<li><DevShelf {indexes} /></li>
		</ul>
		<div class="foot">
			{#if problems}
				<a
					href={problems.href}
					class="problems"
					class:errors={counts.errors > 0}
					class:warnings={!counts.errors && counts.warnings > 0}
					class:current={currentView === 'problems'}
					aria-current={currentView === 'problems' ? 'page' : undefined}
					aria-label="problems: {tally}"
					title="problems: {tally}"
					data-testid="problems-glyph"><Icon name={problems.icon} /></a
				>
			{/if}
			<Settings />
		</div>
	</nav>

	<div class="panel" class:away={!prefs.panel}>
		<div class="head">
			<a href={route('/')} class="name">{label}</a>
			<!-- The panel collapses independently of the split and goes first: on a narrow window it is the column a
			     reader needs least, and the content and the discussion want the width. -->
			<button
				class="fold"
				title={prefs.panel ? 'Hide the panel' : 'Show the panel'}
				aria-label={prefs.panel ? 'Hide the panel' : 'Show the panel'}
				aria-expanded={prefs.panel}
				data-testid="panel-fold"
				onclick={() => (prefs.panel = !prefs.panel)}>{prefs.panel ? '«' : '»'}</button
			>
		</div>
		<div class="sections rail-scroll">
		{#if panel}
			<p class="rail-label">{panelLabel}</p>
			<div class="page-panel rail-scroll">{@render panel()}</div>
		{:else}
			<!-- A page with nothing of its own for the panel gets the documents and the contents. The views are already the strip beside it, and listing them a second time made every such page look like a menu. -->
			{#if docCount}
				<p class="rail-label">
					<button class="shelf" aria-expanded={docsOpen} data-testid="docs-toggle" onclick={() => (docsOpen = !docsOpen)}>
						{docsOpen ? '▾' : '▸'} Documents <span class="aside">({docCount})</span>
					</button>
				</p>
				{#if docsOpen}
					<!-- The contents belong to a document, so they hang off the document rather than standing as a section of
					     their own: a tree of sections floating below an unrelated list never said whose sections they were,
					     and on a corpus of several drafts that is the first question. Only the open document has the
					     disclosure, because it is the only one whose contents this page knows. -->
					{#snippet doc(path: string, href: string, step?: string)}
						{@const here = onDocument && path === currentDoc}
						<li>
							<span class="row">
								<a {href} class:here aria-current={here ? 'page' : undefined}>
									{filename(path)}{#if step}<span class="aside"> @{Number(step)}</span>{/if}
								</a>
								{#if here}
									<button
										class="peek"
										aria-expanded={contentsOpen}
										aria-label={contentsOpen ? 'Hide the contents' : 'Show the contents'}
										title={contentsOpen ? 'Hide the contents' : 'Show the contents'}
										data-testid="contents-toggle"
										onclick={() => (contentsOpen = !contentsOpen)}
									>
										{contentsOpen ? 'hide' : 'show'}<span class="chev" class:down={contentsOpen} aria-hidden="true"></span></button
									>
								{/if}
							</span>
							{#if here && contentsOpen}
								<Contents entries={contents} masterPath={currentDoc} current={currentSection} />
							{/if}
						</li>
					{/snippet}
					{#if masters.length}
						<p class="group">Working Drafts</p>
						<ul class="plain docs" data-testid="docs-drafts">
							{#each masters as m (m.path)}{@render doc(m.path, masterUrl(m.path))}{/each}
						</ul>
					{/if}
					{#if landmarks.length}
						<p class="group">Canon</p>
						<ul class="plain docs" data-testid="docs-canon">
							{#each landmarks as c (c.path)}{@render doc(c.path, canonUrl(c.path), c.step)}{/each}
						</ul>
					{/if}
				{/if}
			{/if}
		{/if}
		{#if statements.length}
			<p class="rail-label">
				<button class="shelf" aria-expanded={nodesOpen} data-testid="nodes-toggle" onclick={() => (nodesOpen = !nodesOpen)}>
					{nodesOpen ? '▾' : '▸'} Nodes <span class="aside">({statements.length})</span>
				</button>
			</p>
			{#if nodesOpen}
				<input class="filter" type="search" placeholder="narrow by id, taxon or title" aria-label="Narrow the nodes" bind:value={nodeFilter} data-testid="nodes-filter" />
				<ul class="plain nodes" data-testid="nodes-list">
					{#each matching.slice(0, NODES_SHOWN) as n (n.id)}
						<li><a href={nodeUrl(n.id)}><code>{n.id}</code> {n.taxon}{n.title ? ' · ' + n.title : ''}</a></li>
					{:else}
						<li class="aside">nothing matches</li>
					{/each}
					{#if matching.length > NODES_SHOWN}<li class="aside">{matching.length - NODES_SHOWN} more; narrow it</li>{/if}
				</ul>
			{/if}
		{/if}
		{#if library.length}
			<p class="rail-label">
				<button class="shelf" aria-expanded={libraryOpen} data-testid="library-toggle" onclick={() => (libraryOpen = !libraryOpen)}>
					{libraryOpen ? '▾' : '▸'} Library <span class="aside">({works.length})</span>
				</button>
			</p>
			{#if libraryOpen}
				<ul class="plain library">
					{#each library as r (r.citekey)}
						<li>
							<a href={workUrl(r.citekey)}>{bibText(r.bib.title) || r.citekey}</a>
							{#if r.unreadable}<span class="aside">unreadable</span>{/if}
						</li>
					{/each}
					{#if more}<li><a href={route('/library')}>all {more} works</a></li>{/if}
				</ul>
			{/if}
		{/if}
		</div>
		<!-- Pinned outside the scroll (S5): writes land in the selected session whatever is shown, so a reader must never go looking for where their work will go. -->
		<div class="write-target"><SessionFooter /></div>
	</div>

	<div class="content">{@render children()}</div>
	{#if rail}<aside class="right rail-scroll">{@render rail()}</aside>{/if}
</div>

<style>
	.shell-c {
		display: grid;
		grid-template-columns: var(--strip) var(--rail-left) minmax(0, 1fr) auto;
		min-height: 100vh;
	}
	/* the column itself goes, not just its contents: a 252px empty gutter is not a collapsed panel */
	.shell-c:has(.panel.away) {
		grid-template-columns: var(--strip) min-content minmax(0, 1fr) auto;
	}
	.strip {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		position: sticky;
		/* both columns are sticky, so each is its own stacking context and the later one would paint over the strip's settings panel */
		z-index: 20;
		top: 0;
		height: 100vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: var(--gap) 0;
		gap: var(--gap);
	}
	.strip ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.strip li {
		height: 26px;
	}
	.strip a,
	.strip button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 26px;
		font-size: 15px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: none;
		border-radius: var(--rad-control);
		cursor: pointer;
	}
	.strip a:hover,
	.strip button:hover {
		color: var(--ink);
		background: var(--sheet);
		text-decoration: none;
	}
	.strip a.current {
		background: var(--link-wash);
		color: var(--link);
	}
	.foot {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
	}
	/* The glyph takes the colour of the worst thing it counts, so whether anything is wrong is legible without a number. */
	.strip a.problems.errors {
		color: var(--state-incomplete);
	}
	.strip a.problems.warnings {
		color: var(--state-stale);
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
	.panel.away {
		padding-left: 4px;
		padding-right: 4px;
	}
	.panel.away .sections,
	.panel.away .write-target,
	.panel.away .name {
		display: none;
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
	.nodes a {
		display: block;
		font-size: 11px;
		color: var(--ink-soft);
		line-height: 1.5;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.nodes code {
		font-size: 9px;
		background: none;
		padding: 0;
	}
	.fold {
		margin-left: auto;
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
	/* **One scroll region, and it is the panel** (plan 0.13 §7). The contents tree used to be squeezed by a panel of
	   fixed height and carry the only scrollbar; adding the Library group then pushed the sections below it off the
	   bottom, because what was squeezed was the tree and not the column. Two scrollbars in a 252px column is also two
	   places to look for the same list. The tree keeps its own class for the other shell, where it is the whole rail. */
	.panel :global(.contents) {
		overflow: visible;
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
		align-items: baseline;
		gap: var(--gap-tight);
		margin-bottom: var(--gap-hair);
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
	/* A group inside Documents. Quieter than a section label, because it names a kind within one list rather than a
	   section of the panel, and the two must not read as peers. */
	.group {
		font-size: 9px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		margin: var(--gap-hair) 0 0 6px;
	}
	/* The document being read carries the same weight as the current section in the contents, because they are the same
	   fact told twice: where you are. */
	.docs a.here {
		color: var(--ink);
		font-weight: 600;
	}
	/* The name takes the width it needs and the disclosure sits at the far edge, so the chevron is in the same place
	   whatever the file is called. */
	.docs .row {
		display: flex;
		align-items: baseline;
		gap: var(--gap-hair);
	}
	.docs .row a {
		flex: 1 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.peek {
		flex: none;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font: inherit;
		font-size: 10px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 2px 4px;
		cursor: pointer;
		border-radius: var(--rad-control);
	}
	.peek:hover,
	.peek[aria-expanded='true'] {
		color: var(--ink);
	}
	/* Drawn rather than set: no chevron in the type stack is a true right angle with equal arms, and the ones that come
	   close carry their font's own weight and side bearings. Two borders on a square rotated 45° are exactly that shape
	   at any size, and they take the colour of the text they sit beside. */
	.chev {
		width: 5px;
		height: 5px;
		border-right: 1.5px solid currentColor;
		border-bottom: 1.5px solid currentColor;
		transform: rotate(-45deg);
		/* the arms hang below the box's centre once rotated; this puts the vertex back on the text's midline */
		margin-bottom: 1px;
	}
	.chev.down {
		transform: rotate(45deg);
		margin-bottom: 3px;
	}
	/* The tree is a child of the row it hangs from, and reads as one: indented under the name, without the section gap
	   that separates the panel's own groups. */
	.docs :global(.contents) {
		margin: var(--gap-hair) 0 var(--gap-tight) 6px;
	}
	.library .aside,
	.docs .aside {
		margin-left: 0.3em;
		color: var(--ink-faint);
		font-size: 0.9em;
	}
</style>
