<script lang="ts">
	// The display preferences (book 15.7): shell, typeface, size, line width, theme, and where comments stand. Every control writes through `prefs`, which applies the data-* attributes and persists. Nothing here is published anywhere; the corpus is read-only to arras.
	import { prefs, type Shell, type Face, type Size, type Width, type Theme, type Format, type Comments } from '$lib/prefs.svelte';
	import { dismiss } from '$lib/dismiss';

	// The icon strip puts its settings at the foot of a full-height column, so a panel hung below the button would open past the bottom of the window.
	let { placement = 'below' }: { placement?: 'below' | 'above' } = $props();

	let open = $state(false);

	const SHELLS: { v: Shell; label: string }[] = [
		{ v: 'a', label: 'rail' },
		{ v: 'c', label: 'strip' }
	];
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
	const FORMATS: { v: Format; label: string }[] = [
		{ v: 'paper', label: 'paper' },
		{ v: 'blog', label: 'blog' }
	];
	const COMMENTS: { v: Comments; label: string }[] = [
		{ v: 'margin', label: 'margin' },
		{ v: 'inline', label: 'inline' },
		{ v: 'hover', label: 'hover' }
	];
</script>

<div class="settings" use:dismiss={() => (open = false)}>
	<button
		class="toggle"
		aria-label="Display settings"
		aria-expanded={open}
		title="Display settings"
		onclick={() => (open = !open)}
		data-testid="settings-toggle">⚙</button
	>
	{#if open}
		<div class="panel" class:above={placement === 'above'} data-testid="settings-panel">
			{#snippet row(label: string, options: { v: string; label: string }[], current: string, pick: (v: string) => void, test: string)}
				<div class="row" role="group" aria-label={label}>
					<span class="lbl">{label}</span>
					<div class="opts">
						{#each options as o (o.v)}
							<button
								class:on={current === o.v}
								aria-pressed={current === o.v}
								onclick={() => pick(o.v)}
								data-testid={test ? `${test}-${o.v}` : undefined}>{o.label}</button
							>
						{/each}
					</div>
				</div>
			{/snippet}

			{@render row('Shell', SHELLS, prefs.shell, (v) => (prefs.shell = v as Shell), 'shell')}
			{@render row('Type', FACES, prefs.face, (v) => (prefs.face = v as Face), 'face')}
			{@render row('Size', SIZES, prefs.size, (v) => (prefs.size = v as Size), 'size')}
			{@render row('Width', WIDTHS, prefs.width, (v) => (prefs.width = v as Width), 'width')}
			{@render row('Theme', THEMES, prefs.theme, (v) => (prefs.theme = v as Theme), 'theme')}
			{@render row('Format', FORMATS, prefs.format, (v) => (prefs.format = v as Format), 'format')}
			{@render row('Comments', COMMENTS, prefs.comments, (v) => (prefs.comments = v as Comments), 'comments')}
		</div>
	{/if}
</div>

<style>
	.settings {
		position: relative;
	}
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
	.panel {
		position: absolute;
		z-index: 40;
		right: 0;
		top: calc(100% + 4px);
		max-height: 80vh;
		overflow-y: auto;
		/* The containing block is the control, which in the icon strip is 44px wide, so a shrink-to-fit box is clamped to nothing and its rows spill out of it. `max-content` sizes the panel to the widest row instead, whatever the control it hangs off. */
		width: max-content;
		max-width: min(92vw, 420px);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		box-shadow: 0 6px 20px rgb(0 0 0 / 12%);
		padding: var(--gap);
		display: grid;
		gap: var(--gap-tight);
	}
	.panel.above {
		top: auto;
		bottom: calc(100% + 4px);
		right: auto;
		left: 0;
	}
	/* One fixed label column, so every row's options start at the same place. */
	.row {
		display: grid;
		grid-template-columns: 4.6rem minmax(0, 1fr);
		align-items: center;
		gap: var(--gap-tight);
	}
	.lbl {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
	}
	.opts {
		display: flex;
		flex-wrap: nowrap;
		gap: var(--gap-hair);
	}
	.opts button {
		white-space: nowrap;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 2px 8px;
		cursor: pointer;
	}
	.opts button:hover {
		color: var(--ink);
	}
	.opts button.on {
		background: var(--link-wash);
		border-color: var(--link);
		color: var(--link);
	}
</style>
