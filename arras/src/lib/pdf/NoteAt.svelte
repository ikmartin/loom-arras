<script lang="ts">
	// The composer (annotation study fixes 5 and 18–21): what opens when a reader selects on a page or draws a box — on a cited work's page, or on a node's or a document's text, where the place is a key of the corpus and the quote is the selection's TeX.
	//
	// **The place stays lit and the composer is only what is said about it.** The words selected, or the box drawn, stay marked on the page while the composer is open (`fragments/pending.ts`); the header names them — the quoted words and the place they are in, or the whole of the place, or the page and a box — and never the place's key. The quilt's annotation types are a row of buttons, each in its look's colour, then No type, which is chosen until the reader picks another; the type is sent by its id, and loom gives the annotation the type's look, or its plain one for none. Words are needed only for a type that stays open until resolved. × and Escape cancel; nothing is written until Annotate is pressed. On the corpus's own text the quote is checked by loom against the source when it is written, and a quote loom cannot find is refused in loom's words with the offer to annotate the whole place instead, so nothing is filed as anchored that is not. The document the place is read in, when there is one, travels with the write as `in`, so the annotation is filed with that document.
	//
	// It stands where the selection is, inset from the window like a floating box, because a form that opened in the pane beside would ask the eye to leave the sentence it is about.
	import { onMount } from 'svelte';
	import { write, type WriteResult } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import NoSession from '$lib/sessions/NoSession.svelte';
	import { writable } from '$lib/sessions/sessions.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { colorOf } from '$lib/review/annotationTypes';
	import type { Look } from '$lib/manifest/types';
	import { quote } from '$lib/notes';

	let {
		citekey = '',
		page = 0,
		target = '',
		name = '',
		in: inDoc = '',
		text = '',
		rects = undefined,
		at,
		onwritten,
		onclose
	}: {
		/** A cited work's page: the work and the page the place is on. */
		citekey?: string;
		page?: number;
		/** Or a key of the corpus — a node, a proof, an equation, a document — for a place on its own text. */
		target?: string;
		/** How the reader names the key, for the header. */
		name?: string;
		/** The document the place is being read in, when it is one: the annotation is filed with it. Empty on a node's own page. */
		in?: string;
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

	/** On a cited work's page, what loom found for the place before anything is written, in its own words. */
	let located = $state('');
	let message = $state('');
	/** The chosen type's id; '' for none. */
	let type = $state('');
	let busy = $state(false);
	let said = $state('');
	/** A quote loom could not find: the offer is to annotate the whole place instead. */
	let unanchored = $state(false);
	// An annotation is a write, so it needs an open session selected like any other (plan 0.13.1).
	const why = $derived(writable(store.manifest));
	const types = $derived(store.manifest?.annotation_types ?? []);
	const chosen = $derived(types.find((t) => t.id === type));
	/** Loom refuses an annotation of a type that stays open without words saying what is to be done. */
	const wordless = $derived(!!chosen?.open && !message.trim());
	let form = $state<HTMLFormElement | null>(null);
	let body = $state<HTMLTextAreaElement | null>(null);

	interface Located {
		anchor?: { basis?: string };
		text?: string;
	}

	onMount(() => {
		body?.focus();
		if (target) return;
		// the preview: what loom found on the page for this place, in loom's own words
		void write('locate', rects ? { citekey, page, rects } : { citekey, page, text }).then((res: WriteResult & Located) => {
			located = (res.ok ? res.result : res.error?.message) ?? '';
		});
	});

	/** Beside the place, and never off the window: below it when there is room, above it otherwise. */
	const style = $derived.by(() => {
		const w = Math.min(504, (typeof window !== 'undefined' ? window.innerWidth : 1000) - 2 * INSET);
		const vw = typeof window !== 'undefined' ? window.innerWidth : 1000;
		const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
		const h = form?.offsetHeight ?? 200;
		let left = Math.max(INSET, Math.min(at.left, vw - w - INSET));
		let top = at.top + at.height + INSET;
		if (top + h > vh - INSET && at.top - h - INSET > INSET) top = at.top - h - INSET;
		top = Math.max(INSET, top);
		return `left: ${left}px; top: ${top}px; width: ${w}px;`;
	});

	/** A type's button, and the form once it is chosen, in the look's colour: its line for the words, its band for the wash. */
	const tint = (look?: Look) => (look ? `--k: var(--ann-${colorOf(look)}); --k-wash: color-mix(in srgb, var(--ann-${colorOf(look)}-band) 45%, transparent);` : '');

	async function submit(e: SubmitEvent, whole = false): Promise<void> {
		e.preventDefault();
		if (why || wordless || busy) return;
		busy = true;
		said = '';
		// `in` goes with a place inside a document, never with the document itself as the place
		const place = target
			? { target, ...(text && !whole ? { quote: text } : {}), ...(inDoc && inDoc !== target ? { in: inDoc } : {}) }
			: { target: citekey, page, ...(rects ? { rects } : { quote: text }) };
		const res: WriteResult = await write('annotate', {
			...place,
			...(message.trim() ? { message: message.trim() } : {}),
			...(type ? { type } : {})
		});
		busy = false;
		if (!res.ok) {
			said = res.error?.message ?? 'the publisher refused it';
			// the offer answers one refusal only: a quote loom could not find, not a document it would not file under
			unanchored = !!target && !!text && !whole && /quote/i.test(said);
			return;
		}
		const id = (res.result ?? '').split(/\s+/)[0] ?? '';
		onwritten?.({ id });
	}

	/** A note in place of an annotation: the place quoted, what was typed as its words, no type (plan 0.22.8). */
	async function quoting(): Promise<void> {
		if (why || busy) return;
		busy = true;
		said = '';
		const place = target
			? { target, ...(text ? { quote: text } : {}) }
			: { target: citekey, page, ...(rects ? { rects } : { quote: text }) };
		const refused = await quote({ ...place, body: message.trim() || undefined });
		busy = false;
		if (refused) {
			said = refused;
			return;
		}
		onwritten?.({ id: '' });
	}

	function keys(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose?.();
		}
	}
</script>

<svelte:window onkeydown={keys} />

<form class="note-at" style="{style} {tint(chosen?.look)}" bind:this={form} onsubmit={submit} data-testid="note-at" aria-label="Annotate this place">
	<p class="place">
		<span class="where" data-testid="note-where">
			{#if target}
				{#if text}
					<span class="lead">on</span> <q class="quoted"><TexProse {text} /></q> <span class="tail">in {name || target}</span>
				{:else}
					<span class="tail">on the whole of {name || target}</span>
				{/if}
			{:else if rects}
				<span class="tail">on p. {page}, a box</span>
			{:else}
				<span class="lead">on p. {page},</span> <q class="quoted">{text}</q>
			{/if}
		</span>
		<button type="button" class="close" title="Cancel (Escape)" aria-label="Cancel" data-testid="note-close" onclick={() => onclose?.()}>×</button>
	</p>
	{#if located}<p class="located" data-testid="note-located">{located}</p>{/if}
	<textarea bind:this={body} bind:value={message} rows="3" placeholder="what you want to say" aria-label="what you want to say" data-testid="note-body"></textarea>
	<div class="kinds" role="group" aria-label="type" data-testid="note-type">
		{#each types as t (t.id)}
			<button type="button" class="k" class:on={type === t.id} aria-pressed={type === t.id} data-type={t.id} style={tint(t.look)} onclick={() => (type = t.id)}>{t.name}</button>
		{/each}
		<button type="button" class="k" class:on={type === ''} aria-pressed={type === ''} data-type="" onclick={() => (type = '')}>No type</button>
	</div>
	<div class="foot">
		<button type="button" class="as-link quote" disabled={!!why || busy} title="A note quoting this place, with no type: an agent reads it with loom since" data-testid="note-quote-it" onclick={quoting}>quote it</button>
		<button type="submit" class="go" disabled={!!why || busy || wordless} title={wordless ? `${chosen?.name} stays open until resolved, so it needs words` : undefined} data-testid="note-submit">{busy ? 'writing…' : 'Annotate'}</button>
	</div>
	{#if said}
		<p class="said" role="status" data-testid="note-said">
			{said}
			{#if unanchored}<button type="button" class="as-link" data-testid="note-whole" onclick={(e) => submit(e as unknown as SubmitEvent, true)}>annotate the whole of {name || target}</button>{/if}
		</p>
	{/if}
	<NoSession />
</form>

<style>
	/* Set 1.2× the viewer's other small controls: the width in the script and every size here, since the composer is where the reader writes. */
	/* The colour is the look's (`tint`): each type's button carries its own, and the form carries the chosen one, which the submit takes; No type is the neutral. */
	.note-at,
	.k {
		--k: var(--ann-neutral);
		--k-wash: var(--ann-neutral-wash);
	}
	.note-at {
		position: fixed;
		z-index: 40;
		display: flex;
		flex-direction: column;
		gap: 9.6px;
		padding: 12px 14.4px;
		background: var(--sheet, #fff);
		border: 1px solid var(--rule, #c9c4b8);
		border-radius: 4.8px;
		box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
		font-family: var(--sans);
		font-size: 15px;
	}
	.place {
		display: flex;
		align-items: baseline;
		gap: 9.6px;
		margin: 0;
		color: var(--ink-faint);
		font-size: 13.2px;
	}
	/* One line: the words are clipped with an ellipsis rather than wrapped, since the selection is still lit on the page and the header only names it. */
	.where {
		flex: 1;
		display: flex;
		align-items: baseline;
		gap: 4.8px;
		min-width: 0;
		white-space: nowrap;
	}
	.quoted {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		font-family: var(--body-face, var(--serif));
		font-style: italic;
		font-size: 15px;
		color: var(--ink-soft);
	}
	.quoted::before { content: '“'; }
	.quoted::after { content: '”'; }
	.lead,
	.tail {
		flex: none;
	}
	.close {
		font: inherit;
		font-size: 16.8px;
		line-height: 1;
		background: none;
		border: 0;
		color: var(--ink-faint);
		cursor: pointer;
		padding: 0 2.4px;
	}
	.close:hover { color: var(--ink); }
	.located {
		margin: -4.8px 0 0;
		font-size: 13.2px;
		color: var(--ink-faint);
	}
	textarea {
		font: inherit;
		font-family: var(--body-face, var(--serif));
		font-size: 16.2px;
		border: 1px solid var(--rule);
		border-radius: 3.6px;
		padding: 7.2px 9.6px;
		background: var(--sheet);
		color: var(--ink);
		resize: vertical;
	}
	.kinds {
		display: flex;
		gap: 4.8px;
		flex-wrap: wrap;
	}
	.k {
		font: inherit;
		font-size: 13.8px;
		padding: 2.4px 10.8px;
		border-radius: 999px;
		border: 1px solid var(--k);
		background: none;
		color: var(--k);
		cursor: pointer;
	}
	.k.on { background: var(--k-wash); }
	.foot {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 9.6px;
		flex-wrap: wrap;
	}
	.go {
		font: inherit;
		font-size: 14.4px;
		padding: 3.6px 14.4px;
		border-radius: 3.6px;
		border: 1px solid var(--k);
		background: var(--k);
		color: #fff;
		cursor: pointer;
	}
	.go:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.said {
		margin: 0;
		color: var(--state-incomplete);
	}
</style>
