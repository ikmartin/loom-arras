<script lang="ts">
	// The nine colours a mark can take, as a row of buttons in the theme's tokens: on the markup bar, on a mark's card and on the selection chip. Pressing one must not end a selection or take the focus from what is being typed, which is why the mousedown is swallowed.
	import { COLOR_NAMES, type MarkColor } from './marks';

	let {
		value,
		onpick
	}: {
		/** The colour held now; '' when none has been chosen, which writes grey. */
		value: MarkColor | '';
		onpick: (color: MarkColor) => void;
	} = $props();

	const titled = (name: string) => name[0].toUpperCase() + name.slice(1);
</script>

<span class="swatches" role="group" aria-label="colour">
	{#each COLOR_NAMES as name (name)}
		<button type="button" class="swatch" class:on={value === name} style="--fill: var(--ann-{name}-band); --edge: var(--ann-{name});" title={titled(name)} aria-label={titled(name)} aria-pressed={value === name} data-testid="swatch-{name}" onmousedown={(e) => e.preventDefault()} onclick={() => onpick(name)}></button>
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
