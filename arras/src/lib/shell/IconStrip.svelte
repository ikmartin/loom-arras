<script lang="ts">
	// Shell C, the default (book 15.2.3): a 44px icon strip of the views this corpus has, search and the settings control, beside a panel holding the page's own panel when it has one and the document's contents otherwise.
	// The strip carries no separate home mark: home is one of the views, and a second control going to the same place is a puzzle, not a shortcut.
	import Contents from './Contents.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { nodeUrl, workUrl } from '$lib/nav';
	import { bibText } from '$lib/works';
	import SessionPicker from '$lib/sessions/SessionPicker.svelte';
	import DocumentPicker from './DocumentPicker.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Settings from './Settings.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { route } from '$lib/paths';
	import type { ShellProps } from './props';

	let { label, views, indexes, currentView, masters, canon, currentDoc, contents, currentSection, counts, search, children, rail, panel, panelLabel }: ShellProps = $props();

	// Sessions stand in the panel whenever the corpus has any: which one is being written to is a standing fact about
	// the corpus, not a property of whichever page is open.
	const sessions = $derived(store.manifest?.sessions ?? []);
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
	let shelf = $state(false);
</script>

<div class="shell-c">
	<nav class="strip" aria-label="Views">
		<ul>
			{#each views as v (v.id)}
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
		</ul>
		<div class="foot"><Settings placement="above" /></div>
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
			<!-- A page with nothing of its own for the panel gets the document and its contents. The views are already the strip beside it, and listing them a second time made every such page look like a menu. -->
			{#if masters.length}
				<p class="rail-label">Document</p>
				<DocumentPicker {masters} {canon} current={currentDoc} />
			{/if}
		{/if}
		{#if statements.length}
			<p class="rail-label">
				<button class="shelf" aria-expanded={nodesOpen} data-testid="nodes-toggle" onclick={() => (nodesOpen = !nodesOpen)}>
					{nodesOpen ? '▾' : '▸'} Nodes <span class="aside">{statements.length}</span>
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
		{#if !panel}
			<p class="rail-label">Contents</p>
			<Contents entries={contents} masterPath={currentDoc} current={currentSection} />
		{/if}
		{#if library.length}
			<p class="rail-label">Library</p>
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
		{#if sessions.length}
			<p class="rail-label">Sessions</p>
			<SessionPicker />
		{/if}
		<!-- The development shelf. Its symbol is deliberately an odd one rather than a designed icon, so that nobody
		     mistakes a shelf we keep while building for part of the interface — and so it is conspicuous on the day it
		     should be taken out. -->
		<p class="rail-label">
			<button class="shelf" aria-expanded={shelf} data-testid="dev-shelf" onclick={() => (shelf = !shelf)}>
				⚗ development
			</button>
		</p>
		{#if shelf}
			<ul class="plain">
				{#each indexes as x (x.href)}
					<li><a href={x.href}>{x.label}</a></li>
				{/each}
			</ul>
		{/if}
		</div>
		<p class="counts" data-testid="counts">{counts.nodes} nodes · {counts.errors} errors · {counts.warnings} warnings</p>
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
	.panel.away {
		padding-left: 4px;
		padding-right: 4px;
	}
	.panel.away .sections,
	.panel.away .counts,
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
	.counts {
		font-size: 10px;
		color: var(--ink-faint);
		margin: auto 0 0;
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
	.library .aside {
		margin-left: 0.3em;
		color: var(--ink-faint);
		font-size: 0.9em;
	}
</style>
