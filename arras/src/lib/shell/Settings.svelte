<script lang="ts">
	// The display preferences (book 15.7): shell, typeface, size, line width, theme, and where comments stand. Every control writes through `prefs`, which applies the data-* attributes and persists. Nothing here is published anywhere; the corpus is read-only to arras.
	import { prefs, type Face, type Size, type Width, type Theme, type Format, type Comments } from '$lib/prefs.svelte';
	import Popover from '$lib/components/Popover.svelte';

	const FACES: { v: Face; label: string }[] = [
		{ v: 'serif', label: 'serif' },
		{ v: 'sans', label: 'sans' }
	];
	const SIZES: { v: Size; label: string }[] = [
		{ v: 's', label: 'S' },
		{ v: 'm', label: 'M' },
		{ v: 'l', label: 'L' }
	];
	const WIDTHS: { v: Width; label: string }[] = [
		{ v: 'narrow', label: 'narrow' },
		{ v: 'mid', label: 'mid' },
		{ v: 'wide', label: 'wide' }
	];
	const THEMES: { v: Theme; label: string }[] = [
		{ v: 'light', label: 'light' },
		{ v: 'dark', label: 'dark' },
		{ v: 'system', label: 'auto' }
	];
	// Four abbreviations, so the row fits beside the others: p1 and p2 are the compiled page, continuous and paginated;
	// b1 and b2 are the two web settings. The titles carry what the letters cannot.
	const FORMATS: { v: Format; label: string; title: string }[] = [
		{ v: 'p1', label: 'p1', title: 'paper, continuous' },
		{ v: 'p2', label: 'p2', title: 'paper, in pages' },
		{ v: 'b1', label: 'b1', title: 'column with a taxon accent' },
		{ v: 'b2', label: 'b2', title: 'wide, with tinted panels' }
	];
	const COMMENTS: { v: Comments; label: string }[] = [
		{ v: 'inline', label: 'inline' },
		{ v: 'floating', label: 'floating' }
	];
</script>

<!-- Above its control: the control stands at the foot of a full-height column, so a panel hung below it would open past the bottom of the window. -->
<Popover placement="above" testid="settings-panel">
	{#snippet trigger({ open, toggle })}
		<button class="toggle" aria-label="Display settings" aria-expanded={open} title="Display settings" onclick={toggle} data-testid="settings-toggle">⚙</button>
	{/snippet}
	<div class="panel">
		{#snippet row(label: string, options: { v: string; label: string; title?: string }[], current: string, pick: (v: string) => void, test: string)}
			<div class="row" role="group" aria-label={label}>
				<span class="lbl">{label}</span>
				<div class="opts">
					{#each options as o (o.v)}
						<button
							class:on={current === o.v}
							aria-pressed={current === o.v}
							onclick={() => pick(o.v)}
							title={o.title}
							data-testid={test ? `${test}-${o.v}` : undefined}>{o.label}</button
						>
					{/each}
				</div>
			</div>
		{/snippet}

		{@render row('Type', FACES, prefs.face, (v) => (prefs.face = v as Face), 'face')}
		{@render row('Size', SIZES, prefs.size, (v) => (prefs.size = v as Size), 'size')}
		{@render row('Width', WIDTHS, prefs.width, (v) => (prefs.width = v as Width), 'width')}
		{@render row('Theme', THEMES, prefs.theme, (v) => (prefs.theme = v as Theme), 'theme')}
		{@render row('Format', FORMATS, prefs.format, (v) => (prefs.format = v as Format), 'format')}
		{@render row('Comments', COMMENTS, prefs.comments, (v) => (prefs.comments = v as Comments), 'comments')}
		<!-- The result keys and states in the left gutter. -->
		{@render row(
			'Show ids',
			[
				{ v: 'no', label: 'no' },
				{ v: 'yes', label: 'yes' }
			],
			prefs.ids ? 'yes' : 'no',
			(v) => (prefs.ids = v === 'yes'),
			'ids'
		)}
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
	/* Sized by its widest row, never by the control it hangs off; rows never wrap (book 15.2.3). */
	.panel {
		width: max-content;
		padding: var(--gap);
		display: grid;
		gap: var(--gap-tight);
	}
	/* One fixed label column, so every row's options start at the same place; wide enough for the longest label, which
	   is what sets it. */
	.row {
		display: grid;
		grid-template-columns: 6.8rem minmax(0, 1fr);
		align-items: center;
		gap: var(--gap-tight);
	}
	.lbl {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
	}
	/* One control per row rather than a row of controls: the options are the values of a single setting, and separate
	   pills read as separate settings. They share one border and one radius, divided by a single rule between
	   neighbours, so the row says `serif | sans` and not `[serif] [sans]`. */
	.opts {
		display: flex;
		flex-wrap: nowrap;
		width: max-content;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		overflow: hidden;
	}
	.opts button {
		white-space: nowrap;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		background: var(--leaf);
		border: none;
		/* the divider belongs to the seam, so the ends of the control stay flush inside its own border */
		border-left: 1px solid var(--rule);
		border-radius: 0;
		padding: 2px 8px;
		cursor: pointer;
	}
	.opts button:first-child {
		border-left: none;
	}
	.opts button:hover {
		color: var(--ink);
		background: var(--sheet);
	}
	.opts button.on {
		background: var(--link-wash);
		color: var(--link);
	}
	/* A selected option's neighbour keeps a divider it can be told apart by: the wash is lighter than the rule. */
	.opts button.on + button {
		border-left-color: var(--link);
	}
</style>
