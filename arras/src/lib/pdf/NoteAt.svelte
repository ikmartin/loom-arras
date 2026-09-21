<script lang="ts">
	// The composer at the place (plan 0.13 §1, item 2): what opens when a reader selects on a page or draws a box.
	//
	// **The reader sees what loom will record before typing.** The selection came from the viewer's own text layer,
	// which is a third extraction of the page; loom maps it against the committed text and the word boxes, and the
	// words it found are shown here as the quote. A box shows the words under it, which is the hint the record keeps.
	// Nothing is written until *note it*; Escape and *cancel* leave nothing behind.
	//
	// It stands where the selection is, inset from the window like a floating box, because a form that opened in the
	// pane beside would ask the eye to leave the sentence it is about.
	import { onMount } from 'svelte';
	import { write, type WriteResult } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import NoSession from '$lib/sessions/NoSession.svelte';
	import { writable } from '$lib/sessions/sessions.svelte';
	import { GRADED, KINDS, SEVERITIES } from '$lib/review/kinds';

	let {
		citekey,
		page,
		text = '',
		rects = undefined,
		at,
		onwritten,
		onclose
	}: {
		citekey: string;
		page: number;
		/** What was selected; empty for a drawn box. */
		text?: string;
		/** What was drawn, in points with the origin at the top left; undefined for a selection. */
		rects?: number[][];
		/** Where the selection or the box is on screen, so the form can stand beside it. */
		at: { left: number; top: number; width: number; height: number };
		onwritten?: (e: { id: string }) => void;
		onclose?: () => void;
	} = $props();

	const INSET = 4;

	let quote = $state('');
	let where = $state('');
	let message = $state('');
	// the initial value only, on purpose: a box is usually a note and a selection usually a question, and the reader picks
	// svelte-ignore state_referenced_locally
	let kind = $state<string>(rects ? 'note' : 'question');
	let severity = $state('');
	let busy = $state(false);
	let said = $state('');
	// A note is a write, so it needs an open session selected like any other (plan 0.13.1).
	let gate = $state<ReturnType<typeof NoSession> | null>(null);
	const why = $derived(writable(store.manifest));
	let form = $state<HTMLFormElement | null>(null);
	let body = $state<HTMLTextAreaElement | null>(null);

	interface Located {
		anchor?: { basis?: string };
		text?: string;
	}

	onMount(() => {
		// the preview: what loom found on the page for this place, in loom's own words
		void write('locate', rects ? { citekey, page, rects } : { citekey, page, text }).then((res: WriteResult & Located) => {
			if (res.ok) {
				quote = res.text ?? text;
				where = res.result ?? '';
			} else {
				quote = text;
				where = res.error?.message ?? '';
			}
		});
		body?.focus();
	});

	/** Beside the place, and never off the window: below it when there is room, above it otherwise. */
	const style = $derived.by(() => {
		const w = Math.min(380, (typeof window !== 'undefined' ? window.innerWidth : 1000) - 2 * INSET);
		const vw = typeof window !== 'undefined' ? window.innerWidth : 1000;
		const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
		const h = form?.offsetHeight ?? 200;
		let left = Math.max(INSET, Math.min(at.left, vw - w - INSET));
		let top = at.top + at.height + INSET;
		if (top + h > vh - INSET && at.top - h - INSET > INSET) top = at.top - h - INSET;
		top = Math.max(INSET, top);
		return `left: ${left}px; top: ${top}px; width: ${w}px;`;
	});

	async function submit(e: SubmitEvent): Promise<void> {
		e.preventDefault();
		if (why) {
			gate?.say();
			return;
		}
		if (!message.trim() || busy) return;
		busy = true;
		said = '';
		const res: WriteResult = await write('comment', {
			target: citekey,
			page,
			...(rects ? { rects } : { quote: text }),
			message: message.trim(),
			kind,
			severity: (GRADED.includes(kind) && severity) || undefined
		});
		busy = false;
		if (!res.ok) {
			said = res.error?.message ?? 'the publisher refused it';
			return;
		}
		const id = (res.result ?? '').split(/\s+/)[0] ?? '';
		onwritten?.({ id });
	}

	function keys(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose?.();
		}
	}
</script>

<svelte:window onkeydown={keys} />

<form class="note-at" {style} bind:this={form} onsubmit={submit} data-testid="note-at" aria-label="Write a note on this place">
	<p class="place">
		<span class="where" data-testid="note-where">{where || `${citekey} p.${page}`}</span>
		<button type="button" class="close" title="Cancel" aria-label="Cancel" onclick={() => onclose?.()}>×</button>
	</p>
	{#if quote}<blockquote class="quote" data-testid="note-quote">{quote}</blockquote>{/if}
	<textarea bind:this={body} bind:value={message} rows="3" required placeholder="what you want to say" data-testid="note-body"></textarea>
	<div class="row">
		<select bind:value={kind} aria-label="kind" data-testid="note-kind">
			{#each KINDS as k (k)}<option value={k}>{k}</option>{/each}
		</select>
		{#if GRADED.includes(kind)}
			<select bind:value={severity} aria-label="severity" data-testid="note-severity">
				{#each SEVERITIES as s (s)}<option value={s}>{s || 'severity'}</option>{/each}
			</select>
		{/if}
		<button type="submit" class:off={!!why} aria-disabled={!!why} disabled={busy || !message.trim()} data-testid="note-submit">{busy ? 'writing…' : 'note it'}</button>
		<button type="button" onclick={() => onclose?.()}>cancel</button>
	</div>
	{#if said}<p class="said" role="status" data-testid="note-said">{said}</p>{/if}
	<NoSession bind:this={gate} placement="below" />
</form>

<style>
	.note-at {
		position: fixed;
		z-index: 40;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 8px 10px;
		background: var(--sheet, #fff);
		border: 1px solid var(--rule-strong, #c9c4b8);
		border-radius: 4px;
		box-shadow: 0 6px 24px rgb(0 0 0 / 14%);
		font-family: var(--sans);
		font-size: 12px;
	}
	.place {
		display: flex;
		align-items: baseline;
		gap: 6px;
		margin: 0;
		color: var(--ink-faint);
	}
	.where {
		flex: 1;
		min-width: 0;
	}
	.close {
		font: inherit;
		background: none;
		border: 0;
		color: var(--ink-faint);
		cursor: pointer;
		padding: 0 2px;
	}
	.quote {
		margin: 0;
		padding: 2px 8px;
		border-left: 3px solid var(--annotation, #c05621);
		color: var(--ink-soft);
		font-family: var(--body-face, serif);
		max-height: 5.5em;
		overflow: auto;
	}
	textarea,
	select {
		font: inherit;
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 3px 5px;
		background: var(--sheet);
		color: var(--ink);
	}
	textarea {
		font-family: var(--body-face, inherit);
		resize: vertical;
	}
	.row {
		display: flex;
		gap: 6px;
		align-items: baseline;
		flex-wrap: wrap;
	}
	.row button {
		font: inherit;
		background: none;
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 2px 8px;
		color: var(--ink-soft);
		cursor: pointer;
	}
	.row button[type='submit'] {
		color: var(--ink);
		border-color: var(--rule-strong);
		margin-left: auto;
	}
	.row button.off {
		opacity: 0.45;
		cursor: not-allowed;
	}
	.row button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.said {
		margin: 0;
		color: var(--annotation, #c05621);
	}
</style>
