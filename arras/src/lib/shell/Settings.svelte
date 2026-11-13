<script lang="ts">
	// Settings, a window over the page (plan 0.23): a left panel of sections in two groups, Loom and Quilt, and the open section's page, which says where its settings are kept. This browser's preferences apply at once; your name is saved through the publisher; the quilt's settings are a draft until Save, since config.toml is committed and shared. A viewer with no publisher shows the quilt's settings as published, and changes none. The development shelf (threads, tags, taxa, what is in no document) is at the panel's foot: scaffolding kept while building, not part of the interface a reader is meant to learn.
	import Popover from '$lib/components/Popover.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { can, capabilities } from '$lib/write';
	import type { Index } from './views';
	import { GROUPS, SECTION, SECTIONS, type SectionId } from './settings/catalog';
	import { draft } from './settings/draft.svelte';
	import Appearance from './settings/Appearance.svelte';
	import Files from './settings/Files.svelte';
	import Profile from './settings/Profile.svelte';
	import General from './settings/General.svelte';
	import Documents from './settings/Documents.svelte';
	import Agents from './settings/Agents.svelte';
	import Library from './settings/Library.svelte';
	import Problems from './settings/Problems.svelte';
	import Overleaf from './settings/Overleaf.svelte';
	import Annotations from './settings/Annotations.svelte';
	import { settingsAsked } from './settings/opener.svelte';

	let { indexes = [] }: { indexes?: Index[] } = $props();

	const KEY = 'arras.settings';
	let open = $state(false);
	let current = $state<SectionId>(remembered());
	let canSave = $state(false);
	let canName = $state(false);
	let canUpdate = $state(false);
	let canTypes = $state(false);
	/** Whether any loom serves this quilt: read-only then means the one serving it is older than this page. */
	let served = $state(false);
	// asked again at each opening, since the publisher may have restarted under the page since it was last asked
	$effect(() => {
		if (!open) return;
		void Promise.all([can('settings-save'), can('reviewer-settings'), can('agents-update'), can('types-save'), capabilities()]).then(([save, name, update, types, caps]) => {
			canSave = save;
			canName = name;
			canUpdate = update;
			canTypes = types;
			served = !!caps;
		});
	});
	// another control asked for a section: Customize in a format menu asks for Annotations
	$effect(() => {
		if (!settingsAsked.n || !settingsAsked.section) return;
		choose(settingsAsked.section);
		open = true;
	});

	function remembered(): SectionId {
		try {
			const id = globalThis.localStorage?.getItem(KEY);
			if (id && id in SECTION) return id as SectionId;
		} catch {
			// a browser that stores nothing opens on the first section
		}
		return SECTIONS[0].id;
	}
	function choose(id: SectionId): void {
		current = id;
		try {
			globalThis.localStorage?.setItem(KEY, id);
		} catch {
			// remembered for this visit only
		}
	}

	const config = $derived(store.manifest?.config);
	// the quilt's sections need a publisher that says what its config holds
	const available = $derived(SECTIONS.filter((s) => s.group !== 'quilt' || config).map((s) => s.id));
	const shown = $derived(available.includes(current) ? current : available[0]);
	// the open section stays in view, which matters where the sections are a row wider than the window
	let nav = $state<HTMLElement | null>(null);
	$effect(() => {
		void shown;
		nav?.querySelector('button.on')?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
	});
	const attention = $derived<Partial<Record<SectionId, string>>>(config?.agents.stale ? { agents: 'Claude Code holds an older list' } : {});
	// Overleaf shows the pairing and changes nothing, so it is never said to be read-only
	const readOnly = $derived(SECTION[shown].group === 'quilt' && shown !== 'overleaf' && !(shown === 'annotations' ? canTypes : canSave));
</script>

<button class="toggle" aria-label="Settings" aria-haspopup="dialog" aria-expanded={open} title="Settings" onclick={() => (open = !open)} data-testid="settings-toggle">⚙</button>

<Popover modal bind:open label="Settings" testid="settings-window">
	<div class="win">
		<nav bind:this={nav} aria-label="Settings sections" data-testid="settings-nav">
			<h2>Settings</h2>
			{#each GROUPS as g (g.id)}
				{@const items = SECTIONS.filter((s) => s.group === g.id && available.includes(s.id))}
				{#if items.length}
					<div class="group">{g.label}</div>
					{#each items as s (s.id)}
						<button class:on={shown === s.id} aria-current={shown === s.id ? 'page' : undefined} onclick={() => choose(s.id)} data-testid="settings-section-{s.id}">
							<svg viewBox="0 0 24 24" aria-hidden="true"><path d={s.icon} /></svg>{s.label}
							{#if attention[s.id]}<span class="dot" title={attention[s.id]} data-testid="settings-attention"></span>{/if}
						</button>
					{/each}
				{/if}
			{/each}
			{#if indexes.length}
				<div class="dev" data-testid="settings-development">
					<span class="group">Development</span>
					<ul>
						{#each indexes as x (x.href)}<li><a href={x.href}>{x.label}</a></li>{/each}
					</ul>
				</div>
			{/if}
		</nav>
		<section class="main">
			<header>
				<div>
					<h2 data-testid="settings-title">{SECTION[shown].label}</h2>
					<p class="where">{SECTION[shown].where}</p>
				</div>
				<button class="close" aria-label="Close settings" onclick={() => (open = false)}>×</button>
			</header>
			<div class="body" data-testid="settings-page" data-section={shown}>
				{#if readOnly}<p class="note info" data-testid="settings-read-only">{#if served}The loom serving this quilt is older than this page and cannot save these. Stop <code>loom serve</code> and run it again, then reload.{:else}Shown as published. Change these in {shown === 'annotations' ? '.loom/annotation-types.toml' : 'config.toml'}.{/if}</p>{/if}
				{#if config?.warnings.length && SECTION[shown].group === 'quilt'}
					<div class="note warn">config.toml: {config.warnings.join('; ')}</div>
				{/if}
				{#if shown === 'appearance'}<Appearance />
				{:else if shown === 'files'}<Files />
				{:else if shown === 'profile'}<Profile editable={canName} />
				{:else if config && shown === 'general'}<General {config} editable={canSave} />
				{:else if config && shown === 'documents'}<Documents {config} editable={canSave} />
				{:else if shown === 'annotations'}<Annotations editable={canTypes} />
				{:else if config && shown === 'agents'}<Agents {config} editable={canSave} {canUpdate} />
				{:else if shown === 'library'}<Library editable={canSave} />
				{:else if config && shown === 'problems'}<Problems {config} editable={canSave} />
				{:else if config && shown === 'overleaf'}<Overleaf {config} />
				{/if}
			</div>
			{#if draft.count || draft.message}
				<div class="savebar" data-testid="settings-savebar">
					<span class="what" role={draft.message ? 'alert' : undefined}>{draft.message || `${draft.count} unsaved ${draft.count === 1 ? 'change' : 'changes'} to config.toml`}</span>
					<button class="btn" onclick={() => draft.revert()} disabled={draft.busy} data-testid="settings-revert">Revert</button>
					<button class="btn primary" onclick={() => void draft.save()} disabled={draft.busy || !draft.count} data-testid="settings-save">{draft.busy ? 'Saving…' : 'Save'}</button>
				</div>
			{/if}
		</section>
	</div>
</Popover>

<style>
	.toggle {
		background: none;
		border: none;
		color: var(--ink-faint);
		font-size: 14px;
		line-height: 1;
		padding: 4px;
		cursor: pointer;
		border-radius: var(--rad-control);
	}
	.toggle:hover {
		color: var(--ink);
		background: var(--link-wash);
	}

	/* the window: a panel of sections beside the open one's page */
	.win {
		width: min(940px, calc(100vw - 2 * var(--gap)));
		height: min(640px, calc(100dvh - 2 * var(--gap)));
		display: grid;
		grid-template-columns: 228px minmax(0, 1fr);
		font-family: var(--sans);
		color: var(--ink);
		background: var(--sheet);
	}
	nav {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		padding: 16px 10px;
		overflow-y: auto;
	}
	nav h2 {
		font-size: 15px;
		font-weight: 600;
		margin: 2px 8px 12px;
	}
	.group {
		display: block;
		font-size: 10.5px;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
		margin: 14px 10px 4px;
	}
	nav button {
		display: flex;
		align-items: center;
		gap: 9px;
		width: 100%;
		text-align: left;
		font: inherit;
		font-size: 13.5px;
		color: var(--ink-soft);
		background: none;
		border: 0;
		border-radius: 8px;
		padding: 7px 10px;
		cursor: pointer;
	}
	nav button:hover {
		background: var(--link-wash);
		color: var(--ink);
	}
	nav button.on {
		background: var(--sheet);
		color: var(--ink);
		font-weight: 500;
		box-shadow: 0 0 0 1px var(--rule);
	}
	nav svg {
		width: 16px;
		height: 16px;
		flex: none;
		stroke: currentColor;
		fill: none;
		stroke-width: 1.6;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.dot {
		margin-left: auto;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--state-stale);
	}
	.dev {
		margin-top: 18px;
		padding-top: 4px;
		border-top: 1px solid var(--rule);
		font-size: 11.5px;
	}
	.dev ul {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 12px;
		margin: 4px 10px 0;
		padding: 0;
		list-style: none;
	}
	.main {
		display: flex;
		flex-direction: column;
		min-width: 0;
		min-height: 0;
	}
	header {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 22px 28px 10px;
	}
	header h2 {
		margin: 0;
		font-size: 19px;
		font-weight: 600;
	}
	.where {
		margin: 4px 0 0;
		font-size: 12px;
		color: var(--ink-faint);
	}
	.close {
		margin-left: auto;
		font: inherit;
		font-size: 20px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: 0;
		cursor: pointer;
		padding: 4px 8px;
		border-radius: 6px;
	}
	.close:hover {
		background: var(--leaf);
		color: var(--ink);
	}
	.body {
		flex: 1;
		overflow-y: auto;
		padding: 4px 28px 28px;
	}
	/* a change to the quilt's config waits to be saved: the file is committed and shared */
	.savebar {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 28px;
		border-top: 1px solid var(--rule);
		background: var(--paper);
		font-size: 13px;
	}
	.savebar .what {
		color: var(--ink-soft);
		margin-right: auto;
	}

	/* what every page is made of */
	.body :global(.card) {
		border: 1px solid var(--rule);
		border-radius: 12px;
		margin: 14px 0;
	}
	.body :global(h3) {
		font-size: 12px;
		font-weight: 600;
		color: var(--ink-faint);
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 22px 0 6px;
	}
	.body :global(.aside) {
		font-size: 12px;
		color: var(--ink-faint);
		margin: 6px 2px;
	}
	.body :global(.fixed) {
		font-family: var(--mono);
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.body :global(.add) {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 10px;
	}
	.win :global(.note) {
		font-size: 12.5px;
		padding: 10px 12px;
		border-radius: 10px;
		margin: 12px 0;
		line-height: 1.45;
	}
	.win :global(.note.ok) {
		background: var(--state-accepted-wash);
		color: var(--state-accepted);
	}
	.win :global(.note.warn) {
		background: var(--state-stale-wash);
		color: var(--ink);
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.win :global(.note.warn .btn) {
		margin-left: auto;
		flex: none;
	}
	.win :global(.note.info) {
		background: var(--leaf);
		color: var(--ink-soft);
	}
	.win :global(code) {
		font-family: var(--mono);
		font-size: 0.92em;
	}
	.body :global(input.text),
	.body :global(select) {
		font: inherit;
		font-size: 13px;
		padding: 6px 10px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--sheet);
		color: var(--ink);
		width: 15rem;
		max-width: 100%;
		box-sizing: border-box;
	}
	.body :global(input.text.mono) {
		font-family: var(--mono);
		font-size: 12.5px;
	}
	.body :global(input.text.short) {
		width: 7rem;
	}
	.body :global(input.text:disabled),
	.body :global(select:disabled) {
		color: var(--ink-soft);
		background: var(--leaf);
	}

	/* a narrow window: the sections in a row above the page */
	@media (max-width: 720px) {
		.win {
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: auto minmax(0, 1fr);
		}
		nav {
			display: flex;
			align-items: center;
			gap: 4px;
			overflow-x: auto;
			overflow-y: hidden;
			border-right: 0;
			border-bottom: 1px solid var(--rule);
			padding: 8px;
		}
		nav h2,
		nav .group,
		nav .dev {
			display: none;
		}
		nav button {
			width: auto;
			flex: none;
			white-space: nowrap;
		}
		header {
			padding: 14px 16px 6px;
		}
		.body {
			padding: 4px 16px 20px;
		}
		.savebar {
			padding: 10px 16px;
			flex-wrap: wrap;
		}
	}
</style>
