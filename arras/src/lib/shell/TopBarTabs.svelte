<script lang="ts">
	// Shell B (book 15.2.2): a 30px top bar of corpus label, breadcrumb, view tabs and search, over a 160px rail holding contents only.
	import Contents from './Contents.svelte';
	import DocumentPicker from './DocumentPicker.svelte';
	import Settings from './Settings.svelte';
	import { INDEXES } from './views';
	import type { ShellProps } from './props';

	let { label, views, currentView, masters, currentMaster, contents, currentSection, counts, search, children, rail, panel, panelLabel }: ShellProps = $props();
</script>

<div class="shell-b">
	<header class="bar">
		<a href="/" class="name">{label}</a>
		<span class="crumb">/ {masters.find((x) => x.path === currentMaster)?.title || currentMaster || '—'}</span>
		<nav class="tabs" aria-label="Views">
			{#each views as v (v.id)}
				<a href={v.href} class:current={currentView === v.id} aria-current={currentView === v.id ? 'page' : undefined}>{v.label}</a>
			{/each}
		</nav>
		<button class="as-link" onclick={search} aria-label="Search">⌕</button>
		<Settings />
	</header>

	<div class="body">
		<nav class="rail" aria-label="Contents">
			{#if masters.length}<DocumentPicker {masters} current={currentMaster} />{/if}
			{#if panel}
				<p class="rail-label">{panelLabel}</p>
				<div class="page-panel rail-scroll">{@render panel()}</div>
			{/if}
			<p class="rail-label">Contents</p>
			<Contents entries={contents} masterPath={currentMaster} current={currentSection} />
			<ul class="indexes">
				{#each INDEXES as x (x.href)}
					<li><a href={x.href}>{x.label}</a></li>
				{/each}
			</ul>
			<p class="counts" data-testid="counts">{counts.nodes} nodes · {counts.errors} errors · {counts.warnings} warnings</p>
		</nav>
		<div class="content">{@render children()}</div>
		{#if rail}<aside class="right rail-scroll">{@render rail()}</aside>{/if}
	</div>
</div>

<style>
	.bar {
		height: var(--topbar);
		background: var(--leaf);
		border-bottom: 1px solid var(--rule);
		display: flex;
		align-items: center;
		gap: var(--gap-tight);
		padding: 0 var(--gap);
		position: sticky;
		top: 0;
		z-index: 30;
	}
	.name {
		font-size: 12px;
		color: var(--ink);
		font-weight: 500;
	}
	.name:hover {
		text-decoration: none;
	}
	.crumb {
		font-size: 11px;
		color: var(--ink-faint);
	}
	.tabs {
		margin-left: auto;
		display: flex;
		gap: 2px;
	}
	.tabs a {
		font-size: 11px;
		color: var(--ink-soft);
		padding: 3px 8px;
		border-radius: var(--rad-pill);
	}
	.tabs a:hover {
		color: var(--ink);
		text-decoration: none;
	}
	.tabs a.current {
		background: var(--link-wash);
		color: var(--link);
	}
	.body {
		display: grid;
		grid-template-columns: var(--rail-b) minmax(0, 1fr) auto;
		min-height: calc(100vh - var(--topbar));
	}
	.rail {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		padding: var(--gap) 14px;
		position: sticky;
		top: var(--topbar);
		height: calc(100vh - var(--topbar));
		display: flex;
		flex-direction: column;
		gap: var(--gap-tight);
		overflow: hidden;
	}
	.page-panel {
		max-height: 40vh;
	}
	.rail :global(.contents) {
		flex: 1;
		min-height: 0;
	}
	.indexes {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--gap-hair) var(--gap-tight);
	}
	.indexes a {
		font-size: 11px;
		color: var(--ink-soft);
	}
	.counts {
		font-size: 10px;
		color: var(--ink-faint);
		margin: 0;
	}
	button.as-link {
		background: none;
		border: none;
		color: var(--ink-faint);
		font-size: 14px;
		cursor: pointer;
		padding: 2px 4px;
	}
	button.as-link:hover {
		color: var(--ink);
	}
	.content {
		min-width: 0;
	}
	aside.right {
		width: var(--rail-right);
		border-left: 1px solid var(--rule);
		padding: var(--gap);
		position: sticky;
		top: var(--topbar);
		max-height: calc(100vh - var(--topbar));
	}
</style>
