<script lang="ts">
	// The colours a mark can take, as a row of buttons: on the markup bar, on a mark's card and on the selection chip. Pressing one must not end a selection or take the focus from what is being typed, which is why the mousedown is swallowed.
	import { COLOR_NAMES, MARK_COLORS, type MarkColor } from './marks';

	let {
		value,
		neutral = true,
		onpick
	}: {
		/** The colour held now, '' for the neutral. */
		value: MarkColor | '';
		/** Whether the neutral is offered beside the colours. */
		neutral?: boolean;
		onpick: (color: MarkColor | '') => void;
	} = $props();

	const css = (rgb: readonly number[]) => `rgb(${rgb.join(' ')})`;
	const titled = (name: string) => name[0].toUpperCase() + name.slice(1);
</script>

<span class="swatches" role="group" aria-label="colour">
	{#if neutral}
		<button type="button" class="swatch none" class:on={value === ''} title="No colour" aria-label="No colour" aria-pressed={value === ''} data-testid="swatch-none" onmousedown={(e) => e.preventDefault()} onclick={() => onpick('')}></button>
	{/if}
	{#each COLOR_NAMES as name (name)}
		<button type="button" class="swatch" class:on={value === name} style="--fill: {css(MARK_COLORS[name].band)}; --edge: {css(MARK_COLORS[name].line)};" title={titled(name)} aria-label={titled(name)} aria-pressed={value === name} data-testid="swatch-{name}" onmousedown={(e) => e.preventDefault()} onclick={() => onpick(name)}></button>
	{/each}
</span>

<style>
	.swatches {
		display: inline-flex;
		align-items: center;
	}
	.swatch {
		display: grid;
		place-items: center;
		width: 20px;
		height: 20px;
		padding: 0;
		border: 0;
		border-radius: 50%;
		background: none;
		cursor: pointer;
	}
	.swatch::before {
		content: '';
		width: 13px;
		height: 13px;
		box-sizing: border-box;
		border-radius: 50%;
		border: 1px solid var(--edge);
		background: var(--fill);
	}
	.swatch.none {
		--edge: var(--ann-neutral);
		--fill: var(--ann-neutral-wash);
	}
	.swatch:hover::before {
		transform: scale(1.15);
	}
	.swatch.on::before {
		box-shadow: 0 0 0 1.5px var(--sheet, #fff), 0 0 0 3px var(--ink);
	}
	.swatch:focus-visible {
		outline: 2px solid var(--accent);
	}
</style>
