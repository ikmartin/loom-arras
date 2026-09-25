<script lang="ts">
	// The composer (book 15.3.10; annotation study fixes 5 and 18–21): what opens when a reader selects on a page or draws a box — on a cited work's page, or on a node's or a document's text, where the place is a key of the corpus and the quote is the selection's TeX.
	//
	// **The place stays lit and the composer is only what is said about it.** The words selected, or the box drawn, stay marked on the page while the composer is open (`fragments/pending.ts`); the header names them — the quoted words and the place they are in, or the whole of the place, or the page and a box — and never the place's key. The five kinds are a row of buttons in their hues, `note` chosen until the reader picks another; severity is three buttons that stand whatever the kind and take a press only for the two graded kinds, so the form never moves; the submit says the kind's verb. × and Escape cancel; nothing is written until the verb is pressed. On the corpus's own text the quote is checked by loom against the source when it is written, and a quote loom cannot find is refused in loom's words with the offer to annotate the whole place instead, so nothing is filed as anchored that is not. The document the place is read in, when there is one, travels with the write as `in`, so the annotation is filed with that document (book 7).
	//
	// It stands where the selection is, inset from the window like a floating box, because a form that opened in the pane beside would ask the eye to leave the sentence it is about.
	import { onMount } from 'svelte';
	import { write, type WriteResult } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import NoSession from '$lib/sessions/NoSession.svelte';
	import { writable } from '$lib/sessions/sessions.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { GRADED, KINDS, SEVERITIES, VERBS, type Kind } from '$lib/review/kinds';

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
	let kind = $state<Kind>('note');
	let severity = $state('');
	let busy = $state(false);
	let said = $state('');
	/** A quote loom could not find: the offer is to annotate the whole place instead. */
	let unanchored = $state(false);
	// An annotation is a write, so it needs an open session selected like any other (plan 0.13.1).
	const why = $derived(writable(store.manifest));
	const graded = $derived(GRADED.includes(kind));
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

	/** A kind that takes no severity drops the one chosen, so nothing greyed is left looking chosen. */
	function pick(k: Kind): void {
		kind = k;
		if (!GRADED.includes(k)) severity = '';
	}

	async function submit(e: SubmitEvent, whole = false): Promise<void> {
		e.preventDefault();
		if (why || !message.trim() || busy) return;
		busy = true;
		said = '';
		// `in` goes with a place inside a document, never with the document itself as the place
		const place = target
			? { target, ...(text && !whole ? { quote: text } : {}), ...(inDoc && inDoc !== target ? { in: inDoc } : {}) }
			: { target: citekey, page, ...(rects ? { rects } : { quote: text }) };
		const res: WriteResult = await write('annotate', {
			...place,
			message: message.trim(),
			kind,
			severity: (graded && severity) || undefined
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

	function keys(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			onclose?.();
		}
	}
</script>

<svelte:window onkeydown={keys} />

<form class="note-at k-{kind}" {style} bind:this={form} onsubmit={submit} data-testid="note-at" aria-label="Annotate this place">
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
	<textarea bind:this={body} bind:value={message} rows="3" required placeholder="what you want to say" aria-label="what you want to say" data-testid="note-body"></textarea>
	<div class="kinds" role="group" aria-label="kind" data-testid="note-kind">
		{#each KINDS as k (k)}
			<button type="button" class="k k-{k}" class:on={kind === k} aria-pressed={kind === k} data-kind={k} onclick={() => pick(k)}>{k}</button>
		{/each}
	</div>
	<div class="foot">
		<div class="sev" class:off={!graded} role="group" aria-label="severity" data-testid="note-severity">
			{#each SEVERITIES as s (s)}
				<button type="button" class="s" class:on={severity === s} aria-pressed={severity === s} disabled={!graded} data-severity={s} onclick={() => (severity = severity === s ? '' : s)}>{s}</button>
			{/each}
		</div>
		<button type="submit" class="go" disabled={!!why || busy || !message.trim()} data-testid="note-submit">{busy ? 'writing…' : VERBS[kind]}</button>
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
	/* The hue is the kind's (theme.css, 15.6): each kind button carries its own, and the form carries the chosen one, which the severity and the submit take. */
	.k-objection { --k: var(--ann-objection); --k-wash: var(--ann-objection-wash); }
	.k-suggestion { --k: var(--ann-suggestion); --k-wash: var(--ann-suggestion-wash); }
	.k-question { --k: var(--ann-question); --k-wash: var(--ann-question-wash); }
	.k-citation { --k: var(--ann-citation); --k-wash: var(--ann-citation-wash); }
	.k-note { --k: var(--ann-neutral); --k-wash: var(--ann-neutral-wash); }
	/* Set 1.2× the viewer's other small controls: the width in the script and every size here, since the composer is where the reader writes. */
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
	.sev {
		display: flex;
		gap: 2.4px;
		align-items: center;
	}
	.s {
		font: inherit;
		font-size: 13.2px;
		padding: 1.2px 8.4px;
		border: 1px solid var(--rule);
		border-radius: 3.6px;
		background: none;
		color: var(--ink-soft);
		cursor: pointer;
	}
	.s.on {
		background: var(--k-wash);
		color: var(--k);
		border-color: var(--k);
	}
	/* Present but not for this kind: greyed, never removed, so the form never moves as the kind changes. */
	.sev.off .s {
		opacity: 0.35;
		cursor: default;
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
