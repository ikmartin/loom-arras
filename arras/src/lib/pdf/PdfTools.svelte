<script lang="ts">
	// The reading controls, as one row: the two tools, the zoom, and where in the document the reader is.
	//
	// The page and the zoom are typed into rather than only stepped, which is what every desktop PDF viewer does and
	// what a reader on page 1 of 60 needs: `+` twelve times is not navigation. Each box shows the current value while it
	// is not being edited, takes the typed one on Enter or on leaving, and puts the current one back on Escape or on
	// anything that is not a number.
	//
	// Off the paper — a work's digest or its info — the row stays where it was and greys out: a toolbar that vanished and came back would move everything after it, and a greyed control still says what it would act on.
	import Icon from '$lib/components/Icon.svelte';
	import ToolPair from './ToolPair.svelte';
	import { MAX_ZOOM, MIN_ZOOM, type PdfView } from './view.svelte';

	let {
		view,
		of = '',
		disabled = false
	}: {
		view: PdfView;
		/** What the controls act on, for their accessible names: in the rail they stand apart from the paper, so each says whose it is. */
		of?: string;
		/** Nothing to act on here: every control is drawn and none acts. */
		disabled?: boolean;
	} = $props();

	const on = $derived(of ? ` in ${of}` : '');

	// Each box is bound to its own text and refilled from the view whenever it is not being edited. Two things fought the
	// field before: a `value=` bound to a derived string, and a focus handler that rewrote the text as it selected it.
	// Either one turned `140` replaced by `150` into `140150`, which clamped to the maximum. Focus now only selects, and
	// the suffix is stripped when the value is read, so what the reader types is the whole of what is parsed.
	let pageText = $state('1');
	let pageEditing = $state(false);
	$effect(() => {
		if (!pageEditing) pageText = String(view.page || 1);
	});

	let zoomText = $state('100%');
	let zoomEditing = $state(false);
	$effect(() => {
		if (!zoomEditing) zoomText = `${Math.round(view.scale * 100)}%`;
	});

	// Escape has to survive the blur it causes: leaving a box commits it, so a cancel that only dropped focus would
	// commit the very value it was cancelling.
	let dropped = false;

	function commitPage(): void {
		pageEditing = false;
		if (dropped) return;
		const n = Number.parseInt(pageText.replace(/[^0-9]/g, ''), 10);
		if (Number.isFinite(n) && n > 0) view.goTo(n);
	}

	function commitZoom(): void {
		zoomEditing = false;
		if (dropped) return;
		const n = Number.parseFloat(zoomText.replace(/[^0-9.]/g, ''));
		if (Number.isFinite(n) && n > 0) view.zoomTo(n / 100);
	}

	const key = (e: KeyboardEvent, commit: () => void) => {
		if (e.key !== 'Enter' && e.key !== 'Escape') return;
		e.preventDefault();
		dropped = e.key === 'Escape';
		commit();
		(e.currentTarget as HTMLInputElement).blur();
		dropped = false;
	};
</script>

<div class="tools" class:disabled role="group" aria-label="reading tools{on}">
	<ToolPair holder={view} {of} {disabled} />

	<span class="bar" aria-hidden="true"></span>

	<button
		type="button"
		class="tool"
		class:on={view.fitWidth}
		title="Match the page to the width of the column"
		aria-label="Match width{on}"
		aria-pressed={view.fitWidth}
		data-testid="zoom-fit"
		{disabled}
		onclick={() => (view.fitWidth = !view.fitWidth)}><Icon name="fit-width" size={15} /></button
	>
	<button type="button" class="step" title="Smaller" aria-label="Smaller{on}" data-testid="zoom-out" {disabled} onclick={() => view.zoomTo(view.scale - 0.1)}>−</button>
	<input
		class="box zoom"
		type="text"
		inputmode="decimal"
		aria-label="Zoom{on}"
		data-testid="zoom-at"
		{disabled}
		bind:value={zoomText}
		onfocus={(e) => ((zoomEditing = true), e.currentTarget.select())}
		onblur={commitZoom}
		onkeydown={(e) => key(e, commitZoom)}
	/>
	<button type="button" class="step" title="Larger" aria-label="Larger{on}" data-testid="zoom-in" {disabled} onclick={() => view.zoomTo(view.scale + 0.1)}>+</button>

	<span class="bar" aria-hidden="true"></span>

	<input
		class="box page"
		type="text"
		inputmode="numeric"
		aria-label="Page{on}"
		data-testid="page-at"
		{disabled}
		bind:value={pageText}
		onfocus={(e) => ((pageEditing = true), e.currentTarget.select())}
		onblur={commitPage}
		onkeydown={(e) => key(e, commitPage)}
	/>
	<span class="of" data-testid="page-count">/ {view.count || '–'}</span>
</div>

<style>
	.tools {
		display: flex;
		align-items: center;
		gap: 3px;
		white-space: nowrap;
	}
	button {
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}
	button:hover:not(:disabled) {
		color: var(--ink);
		background: var(--leaf);
	}
	button:disabled,
	input:disabled {
		cursor: default;
	}
	.tools.disabled > :not(.bar) {
		opacity: 0.35;
	}
	/* every icon control is the same square, so the row reads as one set of tools */
	.tool {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 22px;
		padding: 0;
	}
	.tool.on {
		background: var(--accent-wash);
		color: var(--ink);
	}
	.step {
		width: 20px;
		height: 22px;
		padding: 0;
		font-size: 1.1em;
		line-height: 1;
	}
	/* The typed boxes, as a desktop viewer draws them: a filled field that reads as editable without a full border. */
	.box {
		font: inherit;
		color: var(--ink);
		background: var(--leaf);
		border: 1px solid transparent;
		border-radius: 4px;
		height: 22px;
		padding: 0 6px;
		text-align: center;
	}
	.box:hover:not(:disabled) {
		border-color: var(--rule);
	}
	.box:focus {
		outline: none;
		border-color: var(--accent);
		background: var(--sheet);
	}
	.zoom {
		width: 4.4em;
	}
	.page {
		width: 3em;
	}
	.of {
		color: var(--ink-faint);
		padding-right: 2px;
	}
	.bar {
		width: 1px;
		height: 14px;
		margin: 0 6px;
		background: var(--rule);
	}
</style>
