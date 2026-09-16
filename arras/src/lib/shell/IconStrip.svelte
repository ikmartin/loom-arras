<script lang="ts">
	// Shell C, the default (book 15.2.3): a 44px icon strip beside a 168px panel whose contents follow the view.
	import Contents from './Contents.svelte';
	import DocumentPicker from './DocumentPicker.svelte';
	import Settings from './Settings.svelte';
	import { INDEXES } from './views';
	import type { ShellProps } from './props';

	let { label, views, currentView, masters, currentMaster, contents, currentSection, counts, search, children, rail }: ShellProps = $props();

	// The panel shows the document and its contents in the views that are about a document, and the indexes elsewhere; every shell holds the same elements, so both are always reachable (15.2).
	const documentish = $derived(currentView === 'read' || currentView === 'graph' || currentView === 'home');
</script>

<div class="shell-c">
	<nav class="strip" aria-label="Views">
		<a class="home" href="/" aria-label="Home" title={label}>◆</a>
		<ul>
			{#each views as v (v.id)}
				<li>
					<a
						href={v.href}
						aria-label={v.label}
						title={v.label}
						class:current={currentView === v.id}
						aria-current={currentView === v.id ? 'page' : undefined}
						data-testid="view-{v.id}"><span aria-hidden="true">{v.icon}</span></a
					>
				</li>
			{/each}
			<li><button onclick={search} aria-label="Search" title="search"><span aria-hidden="true">⌕</span></button></li>
		</ul>
		<div class="foot"><Settings /></div>
	</nav>

	<div class="panel">
		<div class="head">
			<a href="/" class="name">{label}</a>
		</div>
		{#if documentish}
			{#if masters.length}
				<p class="rail-label">Document</p>
				<DocumentPicker {masters} current={currentMaster} />
			{/if}
			<p class="rail-label">Contents</p>
			<Contents entries={contents} masterPath={currentMaster} current={currentSection} />
		{:else}
			<p class="rail-label">Views</p>
			<ul class="plain">
				{#each views as v (v.id)}
					<li><a href={v.href} class:current={currentView === v.id}>{v.label}</a></li>
				{/each}
			</ul>
		{/if}
		<p class="rail-label">Indexes</p>
		<ul class="plain">
			{#each INDEXES as x (x.href)}
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
	.home {
		color: var(--ink-soft);
	}
	.foot {
		margin-top: auto;
	}
	.panel {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		padding: var(--gap) 14px;
		position: sticky;
		top: 0;
		height: 100vh;
		display: flex;
		flex-direction: column;
		gap: var(--gap-hair);
		overflow: hidden;
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
	ul.plain a.current {
		background: var(--link-wash);
		color: var(--link);
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
