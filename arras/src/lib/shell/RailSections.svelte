<script lang="ts">
	// Shell A (book 15.2.1): one 178px rail of stacked labelled sections, no top bar.
	import Icon from '$lib/components/Icon.svelte';
	import Contents from './Contents.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import SessionPicker from '$lib/sessions/SessionPicker.svelte';
	import DocumentPicker from './DocumentPicker.svelte';
	import Settings from './Settings.svelte';
	import { route } from '$lib/paths';
	import type { ShellProps } from './props';

	let { label, views, indexes, currentView, masters, canon, currentDoc, contents, currentSection, counts, search, children, rail, panel, panelLabel }: ShellProps = $props();

	const sessions = $derived(store.manifest?.sessions ?? []);
</script>

<div class="shell-a">
	<nav class="rail" aria-label="Navigation">
		<div class="corpus">
			<a href={route('/')} class="name">{label}</a>
			<Settings />
		</div>

		<section>
			<p class="rail-label">View</p>
			<ul class="views">
				{#each views as v (v.id)}
					<li>
						<a href={v.href} class:current={currentView === v.id} aria-current={currentView === v.id ? 'page' : undefined}>
							<span class="icon"><Icon name={v.icon} size={14} /></span>{v.label}
						</a>
					</li>
				{/each}
				<li>
					<button class="as-link" onclick={search}><span class="icon"><Icon name="search" size={14} /></span>search</button>
				</li>
			</ul>
		</section>

		{#if masters.length}
			<section>
				<p class="rail-label">Document</p>
				<DocumentPicker {masters} {canon} current={currentDoc} />
			</section>
		{/if}

		{#if panel}
			<section class="page-panel rail-scroll">
				<p class="rail-label">{panelLabel}</p>
				{@render panel()}
			</section>
		{/if}

		<section class="contents-section">
			<p class="rail-label">Contents</p>
			<Contents entries={contents} masterPath={currentDoc} current={currentSection} />
		</section>

		{#if sessions.length}
			<section>
				<p class="rail-label">Sessions</p>
				<SessionPicker />
			</section>
		{/if}

		<section>
			<p class="rail-label">Indexes</p>
			<ul class="views small">
				{#each indexes as x (x.href)}
					<li><a href={x.href}>{x.label}</a></li>
				{/each}
			</ul>
		</section>

		<p class="counts" data-testid="counts">{counts.nodes} nodes · {counts.errors} errors · {counts.warnings} warnings</p>
	</nav>

	<div class="content">{@render children()}</div>
	{#if rail}<aside class="right rail-scroll">{@render rail()}</aside>{/if}
</div>

<style>
	.shell-a {
		display: grid;
		grid-template-columns: var(--rail-a) minmax(0, 1fr) auto;
		min-height: 100vh;
	}
	.rail {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		padding: var(--gap) 14px;
		position: sticky;
		top: 0;
		height: 100vh;
		display: flex;
		flex-direction: column;
		gap: 10px;
		overflow: hidden;
	}
	.corpus {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--gap-hair);
	}
	.name {
		font-size: 13px;
		color: var(--ink);
		font-weight: 500;
	}
	.name:hover {
		text-decoration: none;
	}
	.page-panel {
		max-height: 40vh;
	}
	.contents-section {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
	}
	.contents-section :global(.contents) {
		flex: 1;
		min-height: 0;
	}
	.counts {
		font-size: 10px;
		color: var(--ink-faint);
		margin: 0;
	}
	ul.views {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	ul.views a,
	ul.views button {
		display: flex;
		align-items: baseline;
		gap: var(--gap-tight);
		width: 100%;
		font-family: var(--sans);
		font-size: 13px;
		color: var(--ink-soft);
		padding: 2px 6px;
		border-radius: var(--rad-pill);
	}
	ul.views.small a {
		font-size: 11px;
	}
	ul.views a:hover,
	ul.views button:hover {
		color: var(--ink);
		background: var(--sheet);
		text-decoration: none;
	}
	ul.views a.current {
		background: var(--link-wash);
		color: var(--link);
	}
	.icon {
		/* a fixed box so every label starts at the same x, whatever the drawing inside it */
		width: 15px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--ink-faint);
	}
	ul.views a.current .icon {
		color: var(--link);
	}
	button.as-link {
		background: none;
		border: none;
		text-align: left;
		cursor: pointer;
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
