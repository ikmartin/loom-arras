<script lang="ts">
	// The look controls every annotating surface shares (the format menu, the popup, Settings › Annotations): the nine colours, underline, highlight or strike, a thickness of 1 to 5 whole pixels and an opacity. A range's value is a button that turns into a field, for a number typed rather than dragged to. A highlight has no line, so its thickness is off.
	import Icon from '$lib/components/Icon.svelte';
	import Swatches from '$lib/pdf/Swatches.svelte';
	import type { MarkColor } from '$lib/pdf/marks';
	import type { Look } from '$lib/manifest/types';
	import { colorOf, styleOf } from './annotationTypes';

	let {
		look,
		onpick,
		words = false,
		disabled = false
	}: {
		/** The look shown. */
		look: Look;
		/** One field changed; `done` false while a range is still being dragged, so a caller that writes can wait for the release. */
		onpick: (change: Partial<Look>, done: boolean) => void;
		/** Name each style beside its icon, where there is room. */
		words?: boolean;
		disabled?: boolean;
	} = $props();

	const STYLE_NAMES: [Look['style'], string, string][] = [
		['underline', 'Underline', 'underline'],
		['highlight', 'Highlight', 'highlighter'],
		['strike', 'Strike', 'strike']
	];

	/** The range being typed into, by name; null while both show their values. */
	let typing = $state<'weight' | 'opacity' | null>(null);
	/** A drag's value before it is released, so the number beside the range follows the thumb. */
	let dragging = $state<Partial<Look>>({});

	const RANGES = {
		weight: { label: 'Thickness', min: 1, max: 5, step: 1, unit: ' px', hard: [1, 5] },
		opacity: { label: 'Opacity', min: 20, max: 100, step: 5, unit: '%', hard: [0, 100] }
	} as const;

	function shown(k: 'weight' | 'opacity'): number {
		return dragging[k] ?? look[k];
	}

	function slide(k: 'weight' | 'opacity', v: number, done: boolean): void {
		dragging = done ? {} : { ...dragging, [k]: v };
		onpick({ [k]: v }, done);
	}

	function typed(k: 'weight' | 'opacity', el: HTMLInputElement, save: boolean): void {
		if (typing !== k) return;
		typing = null;
		const n = Math.round(parseFloat(el.value));
		if (!save || Number.isNaN(n)) return;
		const [lo, hi] = RANGES[k].hard;
		onpick({ [k]: Math.min(hi, Math.max(lo, n)) }, true);
	}

	function focus(el: HTMLInputElement): void {
		el.focus();
		el.select();
	}
</script>

<div class="look" data-testid="look-controls">
	<div class="frow">
		<Swatches value={colorOf(look) as MarkColor} onpick={(c) => !disabled && onpick({ color: c }, true)} />
		<span class="seg" role="group" aria-label="Style">
			{#each STYLE_NAMES as [s, name, icon] (s)}
				<button type="button" class:on={styleOf(look) === s} title={name} aria-label={name} aria-pressed={styleOf(look) === s} {disabled} data-testid="style-{s}" onclick={() => onpick({ style: s }, true)}><Icon name={icon} size={13} />{#if words}<span>{name}</span>{/if}</button>
			{/each}
		</span>
	</div>
	<div class="frow pair">
		{#each ['weight', 'opacity'] as const as k (k)}
			{@const r = RANGES[k]}
			{@const off = disabled || (k === 'weight' && styleOf(look) === 'highlight')}
			<label class="rng" class:off>
				<span class="lab">{r.label}</span>
				<input type="range" min={r.min} max={r.max} step={r.step} value={shown(k)} disabled={off} aria-label={r.label} data-testid="look-{k}" oninput={(e) => slide(k, +e.currentTarget.value, false)} onchange={(e) => slide(k, +e.currentTarget.value, true)} />
				{#if typing === k}
					<input class="val" type="text" inputmode="numeric" aria-label="{r.label} value" value={String(shown(k))} use:focus onkeydown={(e) => { e.stopPropagation(); if (e.key === 'Enter') { e.preventDefault(); typed(k, e.currentTarget, true); } else if (e.key === 'Escape') typed(k, e.currentTarget, false); }} onblur={(e) => typed(k, e.currentTarget, true)} />
				{:else}
					<button type="button" class="val" disabled={off} title="Click to enter a value" aria-label="{r.label} {shown(k)}{r.unit}, click to enter a value" data-testid="look-{k}-value" onclick={() => (typing = k)}>{shown(k)}{r.unit}</button>
				{/if}
			</label>
		{/each}
	</div>
</div>

<style>
	.look {
		display: grid;
		gap: 8px;
		font-family: var(--sans);
		font-size: 12px;
		color: var(--ink-soft);
	}
	.frow {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		flex-wrap: wrap;
	}
	.frow.pair {
		display: grid;
		grid-template-columns: 1fr 1fr;
	}
	.seg {
		display: inline-flex;
		border: 1px solid var(--rule);
		border-radius: 6px;
		overflow: hidden;
	}
	.seg button {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		height: 24px;
		padding: 0 7px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.seg button + button {
		border-left: 1px solid var(--rule);
	}
	.seg button.on {
		background: var(--accent-wash);
		color: var(--ink);
	}
	.rng {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 6px;
		min-width: 0;
	}
	.rng.off {
		opacity: 0.45;
	}
	.rng input[type='range'] {
		min-width: 0;
		width: 100%;
		accent-color: var(--ink-soft);
	}
	.val {
		width: 44px;
		box-sizing: border-box;
		font: inherit;
		font-variant-numeric: tabular-nums;
		text-align: right;
		color: var(--ink);
		background: none;
		border: 1px solid transparent;
		border-radius: 4px;
		padding: 1px 3px;
		cursor: text;
	}
	button.val:hover:not(:disabled) {
		border-color: var(--rule);
	}
	input.val {
		border-color: var(--accent);
		background: var(--sheet);
	}
</style>
