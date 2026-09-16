<script lang="ts">
	// The display preferences (book 15.7): shell, typeface, size, line width, theme. Every control writes through `prefs`, which applies the data-* attributes and persists. Nothing here is published anywhere; the corpus is read-only to arras.
	import { prefs, type Shell, type Face, type Size, type Width, type Theme } from '$lib/prefs.svelte';

	// The icon strip puts its settings at the foot of a full-height column, so a panel hung below the button would open past the bottom of the window.
	let { placement = 'below' }: { placement?: 'below' | 'above' } = $props();

	let open = $state(false);

	const SHELLS: { v: Shell; label: string }[] = [
		{ v: 'a', label: 'rail' },
		{ v: 'b', label: 'tabs' },
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
</script>

<div class="settings">
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
			<fieldset>
				<legend>shell</legend>
				{#each SHELLS as o (o.v)}
					<button
						class:on={prefs.shell === o.v}
						aria-pressed={prefs.shell === o.v}
						onclick={() => (prefs.shell = o.v)}
						data-testid="shell-{o.v}">{o.label}</button
					>
				{/each}
			</fieldset>
			<fieldset>
				<legend>type</legend>
				{#each FACES as o (o.v)}
					<button class:on={prefs.face === o.v} aria-pressed={prefs.face === o.v} onclick={() => (prefs.face = o.v)}>{o.label}</button>
				{/each}
			</fieldset>
			<fieldset>
				<legend>size</legend>
				{#each SIZES as o (o.v)}
					<button class:on={prefs.size === o.v} aria-pressed={prefs.size === o.v} onclick={() => (prefs.size = o.v)}>{o.label}</button>
				{/each}
			</fieldset>
			<fieldset>
				<legend>width</legend>
				{#each WIDTHS as o (o.v)}
					<button class:on={prefs.width === o.v} aria-pressed={prefs.width === o.v} onclick={() => (prefs.width = o.v)}>{o.label}</button>
				{/each}
			</fieldset>
			<fieldset>
				<legend>theme</legend>
				{#each THEMES as o (o.v)}
					<button
						class:on={prefs.theme === o.v}
						aria-pressed={prefs.theme === o.v}
						onclick={() => (prefs.theme = o.v)}
						data-testid="theme-{o.v}">{o.label}</button
					>
				{/each}
			</fieldset>
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
		/* A wrapping row lets this shrink-to-fit box settle at its minimum and fold the buttons under each other; with `nowrap` below, the widest row sets the width and a longer option widens the panel instead. The minimum is a little more than the widest row asks for, so the rows are not flush against the edge. */
		min-width: 180px;
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		box-shadow: 0 6px 20px rgb(0 0 0 / 12%);
		padding: var(--gap-gap);
		display: grid;
		gap: var(--gap-tight);
	}
	.panel.above {
		top: auto;
		bottom: calc(100% + 4px);
		right: auto;
		left: 0;
	}
	fieldset {
		border: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: nowrap;
		gap: var(--gap-hair);
		align-items: center;
	}
	legend {
		/* a fieldset renders its legend above the content box, not as a flex item; it needs no width of its own */
		font-size: 9px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	fieldset button {
		white-space: nowrap;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 2px 7px;
		cursor: pointer;
	}
	fieldset button:hover {
		color: var(--ink);
	}
	fieldset button.on {
		background: var(--link-wash);
		border-color: var(--link);
		color: var(--link);
	}
</style>
