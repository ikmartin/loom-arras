<script lang="ts">
	// The card beside a mark (plan 0.28): what it says, who drew it, and erasing it. It also composes what a pin or words on the page say before they exist, and reads out a comment the PDF itself holds.
	//
	// It stands beside the mark and never over it (A5), and follows it as the page scrolls. What was typed is written when the card closes, by a press of Done, by Enter with a modifier, or by looking elsewhere; Escape leaves it as it was.
	import { untrack } from 'svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import type { MarkDesk } from './desk.svelte';

	let { desk }: { desk: MarkDesk } = $props();

	const INSET = 6;
	const WIDTH = 300;
	const mark = $derived(desk.marks.find((m) => m.id === desk.selected) ?? null);
	const open = $derived(!!desk.composing || !!desk.reading || !!mark);
	const NAMES: Record<string, string> = { highlight: 'Highlight', underline: 'Underline', strike: 'Strike-through', pin: 'Comment', ink: 'Ink', text: 'Words on the page', box: 'Box', oval: 'Oval', arrow: 'Arrow' };

	let text = $state('');
	let editing = $state(false);
	let card = $state<HTMLElement | null>(null);
	let area = $state<HTMLTextAreaElement | null>(null);
	let moved = $state(0);

	// the card opens on what the mark says, and opens to writing where it says nothing yet
	$effect(() => {
		const id = desk.selected;
		const composing = desk.composing;
		// once, at opening: a manifest arriving while someone types must not put back what it said
		text = composing ? '' : untrack(() => desk.marks.find((m) => m.id === id)?.body ?? '');
		editing = !!composing;
	});

	$effect(() => {
		if (desk.composing && area) area.focus();
	});

	$effect(() => {
		if (!open) return;
		const bump = () => moved++;
		window.addEventListener('scroll', bump, { capture: true, passive: true });
		window.addEventListener('resize', bump);
		return () => {
			window.removeEventListener('scroll', bump, { capture: true });
			window.removeEventListener('resize', bump);
		};
	});

	/** Below the mark when there is room, above it otherwise, never off the window. */
	const style = $derived.by(() => {
		void moved;
		void text;
		void mark?.rects;
		const at = desk.composing?.at ?? desk.reading?.at ?? document.querySelector(`[data-testid="page-mark-${CSS.escape(desk.selected)}"]`)?.getBoundingClientRect();
		if (!at) return 'visibility: hidden;';
		const h = card?.offsetHeight ?? 140;
		const left = Math.max(INSET, Math.min(at.left, window.innerWidth - WIDTH - INSET));
		let top = at.top + at.height + INSET;
		if (top + h > window.innerHeight - INSET && at.top - h - INSET > INSET) top = at.top - h - INSET;
		return `left: ${left}px; top: ${Math.max(INSET, top)}px; width: ${WIDTH}px;`;
	});

	function close(): void {
		if (desk.composing) {
			void desk.compose(text);
			return;
		}
		if (mark && desk.writes && editing) desk.say(mark.id, text);
		desk.pick('');
	}

	function keys(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			desk.composing = null;
			desk.pick('');
		} else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			close();
		}
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="mark-card" bind:this={card} {style} data-testid="mark-card" onkeydown={keys}>
		{#if desk.reading}
			<header><strong>{desk.reading.subtype}</strong> in this PDF{#if desk.reading.by} · {desk.reading.by}{/if}</header>
			<div class="said" data-testid="mark-card-body">{desk.reading.body}</div>
			<footer>
				<button type="button" class="plain" data-testid="mark-done" onclick={() => desk.pick('')}>Close</button>
			</footer>
		{:else}
			<header>
				<strong>{NAMES[desk.composing?.kind ?? mark?.kind ?? ''] ?? 'Note'}</strong>
				{#if mark?.who}· {mark.who}{/if}
				{#if mark?.when}· {mark.when.slice(0, 10)}{/if}
			</header>
			{#if desk.writes && (editing || !text)}
				<textarea
					bind:this={area}
					bind:value={text}
					rows="2"
					placeholder={desk.composing?.kind === 'text' ? 'What it says on the page' : 'Add a comment'}
					aria-label="What it says"
					data-testid="mark-comment"
					onfocus={() => (editing = true)}
				></textarea>
			{:else if text}
				<button type="button" class="said as-text" data-testid="mark-card-body" disabled={!desk.writes} onclick={() => (editing = true)}><TexProse {text} /></button>
			{/if}
			{#if desk.writes}
				<footer>
					<button type="button" class="plain" data-testid="mark-done" onclick={close}>Done</button>
					{#if mark}<button type="button" class="plain erase" data-testid="mark-erase" onclick={() => desk.erase(mark.id)}>Erase</button>{/if}
				</footer>
			{/if}
		{/if}
	</div>
{/if}

<style>
	.mark-card {
		position: fixed;
		z-index: 40;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 8px 10px;
		font-family: var(--sans);
		font-size: 0.82rem;
		color: var(--ink);
		background: var(--surface, #fff);
		border: 1px solid var(--rule);
		border-radius: 6px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.16);
	}
	header {
		color: var(--ink-soft);
		font-size: 0.78rem;
	}
	header strong {
		color: var(--ink);
		font-weight: 600;
	}
	textarea {
		font: inherit;
		color: inherit;
		background: transparent;
		border: 1px solid var(--rule);
		border-radius: 4px;
		padding: 4px 6px;
		resize: vertical;
	}
	.said {
		white-space: pre-wrap;
		line-height: 1.4;
	}
	.as-text {
		font: inherit;
		color: inherit;
		text-align: left;
		padding: 0;
		background: none;
		border: 0;
		cursor: text;
	}
	footer {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}
	.plain {
		font: inherit;
		color: var(--ink-soft);
		padding: 2px 8px;
		background: none;
		border: 1px solid var(--rule);
		border-radius: 4px;
		cursor: pointer;
	}
	.plain:hover {
		color: var(--ink);
	}
	.erase {
		order: -1;
		margin-right: auto;
	}
</style>
