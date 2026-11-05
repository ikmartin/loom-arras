<script lang="ts">
	// The markup bar (plan 0.27), above the paper while its switch is on: the tools that draw, undo, and what goes to and from a PDF file. A tool stays up until another is chosen, Escape is pressed or it is pressed again, as a highlighter stays in the hand. Where no publisher takes writes only saving a copy and editing pages remain, which need none.
	import Icon from '$lib/components/Icon.svelte';
	import type { MarkDesk } from './desk.svelte';
	import type { PageTool } from './marks';
	import type { PdfView } from './view.svelte';

	let {
		desk,
		view,
		onpages,
		onoutside
	}: {
		desk: MarkDesk;
		view: PdfView;
		/** Open the pages editor. */
		onpages: () => void;
		/** Open the file in its application; absent where it is not a project's file. */
		onoutside?: () => void;
	} = $props();

	const TOOLS: { tool: PageTool; icon: string; title: string }[] = [
		{ tool: 'highlight', icon: 'highlighter', title: 'Highlight: select words and they are marked' },
		{ tool: 'underline', icon: 'underline', title: 'Underline: select words and they are marked' },
		{ tool: 'strike', icon: 'strike', title: 'Strike through: select words and they are marked' },
		{ tool: 'pin', icon: 'pin', title: 'Comment: press where it goes' },
		{ tool: 'ink', icon: 'ink', title: 'Draw freehand' },
		{ tool: 'text', icon: 'type', title: 'Words on the page: press where they go' },
		{ tool: 'rect', icon: 'rect', title: 'Draw a box' },
		{ tool: 'oval', icon: 'oval', title: 'Draw an oval' },
		{ tool: 'arrow', icon: 'arrow', title: 'Draw an arrow' }
	];

	let picker = $state<HTMLInputElement | null>(null);

	function choose(tool: PageTool): void {
		desk.flush();
		desk.pick('');
		view.tool = view.tool === tool ? 'select' : tool;
	}

	$effect(() => {
		if (desk.writes) void desk.countHere();
	});
</script>

<div class="mark-bar" role="toolbar" aria-label="markup" data-testid="markup-bar">
	{#if desk.writes}
		<div class="group">
			{#each TOOLS as t (t.tool)}
				<button type="button" class="tool" class:on={view.tool === t.tool} title={t.title} aria-label={t.title} aria-pressed={view.tool === t.tool} data-testid="tool-{t.tool}" onclick={() => choose(t.tool)}><Icon name={t.icon} size={15} /></button>
			{/each}
		</div>
		<div class="group">
			<button type="button" class="tool" title="Undo" aria-label="Undo" data-testid="mark-undo" disabled={!desk.canUndo} onclick={() => desk.undo()}><Icon name="undo" size={15} /></button>
			<button type="button" class="tool" title="Redo" aria-label="Redo" data-testid="mark-redo" disabled={!desk.canRedo} onclick={() => desk.redo()}><Icon name="redo" size={15} /></button>
		</div>
	{/if}
	<div class="group words">
		<button type="button" class="act" title="Save a copy of this PDF with what is marked written into it" data-testid="mark-save-copy" disabled={desk.busy} onclick={() => desk.saveCopy()}>Save a copy</button>
		{#if desk.writes}
			<button type="button" class="act" title="Take in the annotations of another copy of this PDF, one you marked in Preview or elsewhere" data-testid="mark-take-from" disabled={desk.busy} onclick={() => picker?.click()}>Take in from a PDF…</button>
			{#if desk.here}
				<button type="button" class="act" title="Make the annotations this PDF holds into marks here" data-testid="mark-take-here" disabled={desk.busy} onclick={() => desk.takeHere()}>Take in {desk.here} from this PDF</button>
			{/if}
			<input
				bind:this={picker}
				type="file"
				accept="application/pdf,.pdf"
				hidden
				data-testid="mark-take-file"
				onchange={(e) => {
					const f = e.currentTarget.files?.[0];
					e.currentTarget.value = '';
					if (f) void desk.takeFrom(f);
				}}
			/>
		{/if}
		<button type="button" class="act" title="Turn, delete, reorder or insert pages, into a new file" data-testid="mark-pages" onclick={onpages}>Edit pages…</button>
		{#if onoutside}<button type="button" class="act" title="Open this PDF in its application, for what is not done here" data-testid="mark-outside" onclick={onoutside}>Open in its application</button>{/if}
	</div>
	{#if desk.said}<p class="said" role="status" data-testid="mark-said">{desk.said}</p>{/if}
</div>

<style>
	.mark-bar {
		flex: none;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px 12px;
		padding: 4px 10px;
		font-family: var(--sans);
		font-size: 0.78rem;
		border-bottom: 1px solid var(--rule);
		background: var(--surface, #fff);
	}
	.group {
		display: flex;
		align-items: center;
		gap: 2px;
	}
	.words {
		gap: 6px;
		flex-wrap: wrap;
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
	}
	button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.tool {
		display: flex;
		padding: 4px 5px;
	}
	.tool.on {
		color: var(--ink);
		background: var(--accent-wash);
	}
	.act {
		padding: 2px 6px;
		border: 1px solid var(--rule);
		white-space: nowrap;
	}
	.said {
		flex: 1 1 100%;
		margin: 0;
		color: var(--ink-soft);
	}
</style>
