<script lang="ts">
	// The reading controls, as one row: the two tools, the zoom, and where in the document the reader is.
	//
	// The page and the zoom are typed into rather than only stepped, which is what every desktop PDF viewer does and
	// what a reader on page 1 of 60 needs: `+` twelve times is not navigation. Each box shows the current value while it
	// is not being edited, takes the typed one on Enter or on leaving, and puts the current one back on Escape or on
	// anything that is not a number.
	import Icon from '$lib/components/Icon.svelte';
	import { MAX_ZOOM, MIN_ZOOM, type PdfView } from './view.svelte';

	let { view }: { view: PdfView } = $props();

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

<div class="tools" role="toolbar" aria-label="reading tools">
	<!-- Two icons of one size rather than two words of different lengths: they are a pair of modes, and a pair reads as
	     a pair only when the controls match. -->
	<button
		type="button"
		class="tool"
		class:on={view.tool === 'select'}
		title="Select text — highlight and copy as usual, and annotate what you select. Hold Alt to draw a box without switching."
		aria-label="Select text"
		aria-pressed={view.tool === 'select'}
		data-testid="tool-select"
		onclick={() => (view.tool = 'select')}><Icon name="cursor" size={15} /></button
	>
	<button
		type="button"
		class="tool"
		class:on={view.tool === 'box'}
		title="Draw a box around a formula or a figure. A click without a drag leaves a point."
		aria-label="Draw a box"
		aria-pressed={view.tool === 'box'}
		data-testid="tool-box"
		onclick={() => (view.tool = 'box')}><Icon name="marquee" size={15} /></button
	>

	<span class="bar" aria-hidden="true"></span>

	<button
		type="button"
		class="tool"
		class:on={view.fitWidth}
		title="Match the page to the width of the column"
		aria-label="Match width"
		aria-pressed={view.fitWidth}
		data-testid="zoom-fit"
		onclick={() => (view.fitWidth = !view.fitWidth)}><Icon name="fit-width" size={15} /></button
	>
	<button type="button" class="step" title="Smaller" aria-label="Smaller" data-testid="zoom-out" onclick={() => view.zoomTo(view.scale - 0.1)}>−</button>
	<input
		class="box zoom"
		type="text"
		inputmode="decimal"
		aria-label="Zoom"
		data-testid="zoom-at"
		bind:value={zoomText}
		onfocus={(e) => ((zoomEditing = true), e.currentTarget.select())}
		onblur={commitZoom}
		onkeydown={(e) => key(e, commitZoom)}
	/>
	<button type="button" class="step" title="Larger" aria-label="Larger" data-testid="zoom-in" onclick={() => view.zoomTo(view.scale + 0.1)}>+</button>

	<span class="bar" aria-hidden="true"></span>

	<input
		class="box page"
		type="text"
		inputmode="numeric"
		aria-label="Page"
		data-testid="page-at"
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
		font-size: 0.78rem;
		white-space: nowrap;
	}
	button {
		font: inherit;
		color: var(--ink-soft, #5f5e5a);
		background: none;
		border: none;
		border-radius: 3px;
		cursor: pointer;
	}
	button:hover {
		color: var(--ink, #2c2c2a);
		background: var(--leaf, #f1efe7);
	}
	/* every icon control is the same square, so the row reads as one set of tools */
	.tool {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 20px;
		padding: 0;
	}
	.tool.on {
		background: var(--annotation-tint, rgb(217 119 87 / 0.18));
		color: var(--ink, #2c2c2a);
	}
	.step {
		width: 18px;
		height: 20px;
		padding: 0;
		font-size: 0.95rem;
		line-height: 1;
	}
	/* The typed boxes, as a desktop viewer draws them: a filled field that reads as editable without a full border. */
	.box {
		font: inherit;
		color: var(--ink, #2c2c2a);
		background: var(--leaf, #f1efe7);
		border: 1px solid transparent;
		border-radius: 3px;
		height: 20px;
		padding: 0 4px;
		text-align: center;
	}
	.box:hover {
		border-color: var(--rule, #ddd9cf);
	}
	.box:focus {
		outline: none;
		border-color: var(--accent, #d97757);
		background: var(--sheet, #fff);
	}
	.zoom {
		width: 4.2em;
	}
	.page {
		width: 2.8em;
	}
	.of {
		color: var(--muted, #6b6b6b);
		padding-right: 2px;
	}
	.bar {
		width: 1px;
		height: 15px;
		margin: 0 4px;
		background: var(--rule, #ddd9cf);
	}
</style>
