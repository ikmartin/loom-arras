<script lang="ts">
	// **Changes** on a document's toolbar, with how many changes wait in its text, and its menu: how the text shows them (Markup, every change in place, removed words struck and new words underlined; Final, the text with every change made), and Keep all and Discard all, each saying what it would do. With annotations alone listed the text is as kept, so the views wait. Keep all and Discard all act on the document's changes that are ready, through the same writes as a change's own Keep and Discard (`history.svelte.ts`).
	import Icon from '$lib/components/Icon.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { can } from '$lib/write';
	import { acted } from './acted.svelte';
	import type { Annotating, ChangesView } from './annotating.svelte';
	import { allSays, changesIn, ready } from './changes';
	import { discardChanges, keepChanges } from './history.svelte';
	import { say } from './toasts.svelte';

	let {
		notes,
		document,
		of
	}: {
		notes: Annotating;
		/** The document whose changes these are. */
		document: string;
		/** What it acts on, for its accessible names. */
		of: string;
	} = $props();

	const VIEWS: [ChangesView, string, string][] = [
		['markup', 'Markup', 'Every pending change in place: removed words struck through, new words underlined'],
		['final', 'Final', 'The text with every pending change made, unmarked']
	];

	const list = $derived(changesIn(store.manifest, document).filter((c) => !(c.id in acted.map)));
	const actable = $derived(list.filter(ready));
	const all = $derived(allSays(actable));
	const off = $derived(notes.layer === 'annotations');

	let writes = $state({ keep: false, discard: false });
	$effect(() => {
		void can('change-keep').then((ok) => (writes.keep = ok));
		void can('change-discard').then((ok) => (writes.discard = ok));
	});

	/** The page's document: the prop `document` names the quilt's. */
	const document_ = globalThis.document;

	let open = $state(false);
	let button = $state<HTMLElement | null>(null);
	let menu = $state<HTMLElement | null>(null);
	let place = $state({ left: 0, top: 0 });

	function toggle(): void {
		open = !open;
		if (!open || !button) return;
		const r = button.getBoundingClientRect();
		place = { left: r.left, top: r.bottom + 6 };
	}
	// kept inside the window once its size is known
	$effect(() => {
		const el = menu;
		if (!el) return;
		const left = Math.min(Math.max(12, place.left), window.innerWidth - el.offsetWidth - 12);
		if (left !== place.left) place = { ...place, left };
	});
	// a press elsewhere closes it, and Escape before anything else it would close
	$effect(() => {
		if (!open) return;
		const away = (e: PointerEvent) => {
			const t = e.target as Element | null;
			if (!t?.closest?.('.changes-menu, [data-testid="changes-toggle"]')) open = false;
		};
		const key = (e: KeyboardEvent) => {
			if (e.key !== 'Escape') return;
			e.preventDefault();
			open = false;
		};
		document_.addEventListener('pointerdown', away, true);
		document_.addEventListener('keydown', key, true);
		return () => {
			document_.removeEventListener('pointerdown', away, true);
			document_.removeEventListener('keydown', key, true);
		};
	});

	function show(v: ChangesView): void {
		notes.view = v;
		open = false;
	}

	/** Keep or discard every change of the document that is ready, shown so at once; a refusal is said. */
	async function every(how: 'keep' | 'discard'): Promise<void> {
		open = false;
		notes.close();
		const res = how === 'keep' ? await keepChanges({ all: true, document }) : await discardChanges({ all: true, document });
		const refused = res.refused ?? [];
		if (!res.ok) say({ title: how === 'keep' ? 'Not kept' : 'Not discarded', lines: [res.error?.message ?? 'the publisher refused it'] });
		else if (refused.length) say({ title: `${refused.length} ${refused.length === 1 ? 'change was' : 'changes were'} not ${how === 'keep' ? 'kept' : 'discarded'}`, lines: refused.slice(0, 3).map((r) => r.why) });
	}
</script>

{#if list.length}
	<span class="sep" aria-hidden="true"></span>
	<button type="button" class="tool words" class:on={open} bind:this={button} aria-expanded={open} aria-haspopup="menu" title="Pending changes: how the text shows them, and keeping or discarding them all" aria-label="Changes in {of}, {list.length}" data-testid="changes-toggle" onclick={toggle}><Icon name="pen" size={14} />Changes<span class="badge" data-testid="changes-count">{list.length}</span><Icon name="caret" size={12} /></button>
{/if}

{#if open}
	<div class="changes-menu" bind:this={menu} role="menu" aria-label="Changes in {of}" style="left: {place.left}px; top: {place.top}px;" data-testid="changes-menu">
		<div class="sec">Show the text as</div>
		{#each VIEWS as [v, name, says] (v)}
			<button type="button" class="vrow" class:on={!off && notes.view === v} role="menuitemradio" aria-checked={!off && notes.view === v} disabled={off} data-testid="changes-view-{v}" onclick={() => show(v)}><span class="vn">{name}</span><span class="vd">{says}</span></button>
		{/each}
		{#if off}<div class="vd pad">The list shows annotations only, so the text is as you kept it.</div>{/if}
		<div class="hr"></div>
		<button type="button" class="vrow" role="menuitem" disabled={!actable.length || !writes.keep} data-testid="changes-keep-all" onclick={() => void every('keep')}><span class="vn"><Icon name="check" size={13} />Keep all {actable.length}</span><span class="vd">{all.keep}</span></button>
		<button type="button" class="vrow" role="menuitem" disabled={!actable.length || !writes.discard} data-testid="changes-discard-all" onclick={() => void every('discard')}><span class="vn"><Icon name="close" size={13} />Discard all {actable.length}</span><span class="vd">{all.discard}</span></button>
		{#if actable.length < list.length}<div class="vd pad">{list.length - actable.length} more cannot be kept or discarded now; each says why.</div>{/if}
	</div>
{/if}

<style>
	.sep {
		width: 1px;
		height: 16px;
		margin: 0 5px;
		background: var(--rule);
	}
	.tool {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 5px;
		height: 22px;
		min-width: 24px;
		padding: 0 5px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		border-radius: 4px;
		cursor: pointer;
	}
	.tool:hover {
		color: var(--ink);
		background: var(--leaf);
	}
	.tool.on {
		color: var(--ink);
		background: var(--accent-wash);
	}
	.tool :global(svg:first-child) {
		color: var(--change);
	}
	.badge {
		min-width: 16px;
		padding: 0 5px;
		font-size: 10.5px;
		line-height: 15px;
		text-align: center;
		color: var(--change);
		background: var(--change-wash);
		border: 1px solid color-mix(in srgb, var(--change) 35%, transparent);
		border-radius: 8px;
	}
	.changes-menu {
		position: fixed;
		z-index: 45;
		display: grid;
		gap: 2px;
		box-sizing: border-box;
		width: 330px;
		max-width: calc(100vw - 24px);
		padding: 8px;
		font-family: var(--sans);
		font-size: 12.5px;
		white-space: normal;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 9px;
		box-shadow: var(--float-shadow);
	}
	.sec {
		margin: 2px 8px 4px;
		font-size: 10.5px;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	.vrow {
		display: flex;
		flex-direction: column;
		gap: 1px;
		width: 100%;
		padding: 6px 8px;
		font: inherit;
		text-align: left;
		color: var(--ink);
		background: none;
		border: 0;
		border-radius: 6px;
		cursor: pointer;
	}
	.vrow:hover:not(:disabled) {
		background: var(--leaf);
	}
	.vrow.on {
		background: var(--accent-wash);
	}
	.vrow:disabled {
		opacity: 0.45;
		cursor: default;
	}
	.vn {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-weight: 600;
	}
	.vd {
		font-size: 12px;
		line-height: 1.35;
		color: var(--ink-soft);
	}
	.pad {
		padding: 2px 8px;
	}
	.hr {
		height: 1px;
		margin: 5px 0;
		background: var(--rule);
	}
</style>
