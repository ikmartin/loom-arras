<script lang="ts">
	// The two annotating tools, drawn alike wherever there is something to annotate: a work's pages, a node, a document. Select marks text as a reader marks any text and offers to annotate it; box draws round what text selection cannot reach, a formula or a figure. Alt-drag draws a box from the select tool without switching.
	//
	// Two icons of one size rather than two words of different lengths: they are a pair of modes, and a pair reads as a pair only when the controls match.
	import Icon from '$lib/components/Icon.svelte';
	import type { Tool } from './view.svelte';

	let {
		holder,
		of = '',
		disabled = false
	}: {
		/** Whatever keeps the mode: a work's page view, a node's or a document's state. */
		holder: { tool: Tool };
		/** What the tools act on, for their accessible names. */
		of?: string;
		disabled?: boolean;
	} = $props();

	const on = $derived(of ? ` in ${of}` : '');
</script>

<button
	type="button"
	class="tool"
	class:on={!disabled && holder.tool === 'select'}
	title="Select text, and annotate what you select. Hold Alt to draw a box without switching."
	aria-label="Select text{on}"
	aria-pressed={holder.tool === 'select'}
	data-testid="tool-select"
	{disabled}
	onclick={() => (holder.tool = 'select')}><Icon name="cursor" size={15} /></button
>
<button
	type="button"
	class="tool"
	class:on={!disabled && holder.tool === 'box'}
	title="Draw a box round a formula or a figure, and annotate it."
	aria-label="Draw a box{on}"
	aria-pressed={holder.tool === 'box'}
	data-testid="tool-box"
	{disabled}
	onclick={() => (holder.tool = 'box')}><Icon name="marquee" size={15} /></button
>

<style>
	/* every icon control is the same square, so the row reads as one set of tools */
	.tool {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 22px;
		padding: 0;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}
	.tool:hover:not(:disabled) {
		color: var(--ink);
		background: var(--leaf);
	}
	.tool.on {
		background: var(--accent-wash);
		color: var(--ink);
	}
	.tool:disabled {
		opacity: 0.35;
		cursor: default;
	}
</style>
