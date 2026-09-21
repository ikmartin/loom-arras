<script lang="ts">
	// Shell C, the default (book 15.2.3): a 44px icon strip of the views this corpus has, search and the settings control, beside a panel holding the page's own panel when it has one and the document's contents otherwise.
	// The strip carries no separate home mark: home is one of the views, and a second control going to the same place is a puzzle, not a shortcut.
	import Contents from './Contents.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import SessionPicker from '$lib/sessions/SessionPicker.svelte';
	import DocumentPicker from './DocumentPicker.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Settings from './Settings.svelte';
	import { route } from '$lib/paths';
	import type { ShellProps } from './props';

	let { label, views, indexes, currentView, masters, canon, currentDoc, contents, currentSection, counts, search, children, rail, panel, panelLabel }: ShellProps = $props();

	// Sessions stand in the panel whenever the corpus has any: which one is being written to is a standing fact about
	// the corpus, not a property of whichever page is open.
	const sessions = $derived(store.manifest?.sessions ?? []);
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

	<div class="panel">
		<div class="head">
			<a href={route('/')} class="name">{label}</a>
		</div>
		{#if panel}
			<p class="rail-label">{panelLabel}</p>
			<div class="page-panel rail-scroll">{@render panel()}</div>
		{:else}
			<!-- A page with nothing of its own for the panel gets the document and its contents. The views are already the strip beside it, and listing them a second time made every such page look like a menu. -->
			{#if masters.length}
				<p class="rail-label">Document</p>
				<DocumentPicker {masters} {canon} current={currentDoc} />
			{/if}
			<p class="rail-label">Contents</p>
			<Contents entries={contents} masterPath={currentDoc} current={currentSection} />
		{/if}
		{#if sessions.length}
			<p class="rail-label">Sessions</p>
			<SessionPicker />
		{/if}
		<p class="rail-label">Indexes</p>
		<ul class="plain">
			{#each indexes as x (x.href)}
				<li><a href={x.href}>{x.label}</a></li>
			{/each}
		</ul>
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
	.page-panel {
		flex: 1;
		min-height: 0;
	}
	.panel :global(.contents) {
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
</style>
