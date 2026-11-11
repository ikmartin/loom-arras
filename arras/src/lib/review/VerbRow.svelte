<script lang="ts">
	// The verbs an annotation offers, as one quiet row at the right of its box's meta line, and the place a reply, a restatement or a reason is written: a block that opens inside the box beneath the meta line, so nothing an annotation can do happens outside its box. Each verb is shown only when `GET /_api` says the publisher serves its endpoint.
	//
	// An open annotation offers reply, edit and delete, and resolve only when its type stays open until resolved, since loom refuses to resolve one that only informs. One whose text places offers take it, which writes it in, a version of the document kept first, and resolves it as applied; one with text offers leave it in place of resolve; one whose key already reads as it taken offers resolve as applied, which records the key's hash. Edit restates the body and may change the type. Delete takes the annotation and its replies out of the log at once, and its undo stands in `DeletedBar`, since the box goes with them; loom refuses an agent's delete of what it did not write, and the refusal is shown here. A resolved one offers `reopen` and delete. A reply's own row (`compact`) is edit and delete.
	import { untrack } from 'svelte';
	import { can, known, write } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import { staysOpen } from './annotationTypes';
	import { deleteAnnotation } from './deleted.svelte';
	import { linkName } from '$lib/workspace/names';
	import { drafts, type Verb } from './drafts';
	import type { Annotation } from '$lib/manifest/types';

	let {
		annotation,
		compact = false
	}: {
		annotation: Annotation;
		/** A reply's own row: edit and delete. */
		compact?: boolean;
	} = $props();

	//: Seeded from the probe's standing answer, so a row re-mounted after a write does not blink out while it asks again.
	const ENDPOINTS = ['reply', 'edit', 'resolve', 'delete', 'suggestion-apply'];
	let allowed = $state<Record<string, boolean>>(
		Object.fromEntries(ENDPOINTS.map((v) => [v, known(v) ?? false]).filter(([, ok]) => ok))
	);
	// a box made again -- which happens whenever a new manifest arrives -- opens on what was being written in it
	const kept = untrack(() => drafts.get(annotation.id));
	let open = $state<Verb | null>(kept?.open ? kept.verb : null);
	let busy = $state(false);
	let said = $state('');
	let text = $state(kept?.text ?? '');
	/** The type an edit sets: an id of the quilt's types, or '' for none. */
	let type = $state(kept?.type ?? untrack(() => annotation.type) ?? '');

	$effect(() => {
		const verb = open;
		const now = { text, type };
		const was = drafts.get(annotation.id);
		if (verb) drafts.set(annotation.id, { verb, ...now, open: true, focused: was?.focused ?? false, caret: was?.caret ?? now.text.length });
		else if (was) was.open = false;
	});

	/** Record where the cursor is, so a box made again can put it back. A textarea taken out of the page with its box is not a reader leaving it, so a blur counts only while it is still on the page. */
	function track(el: HTMLTextAreaElement) {
		const note = () => {
			const d = drafts.get(annotation.id);
			if (d) (d.focused = document.activeElement === el), (d.caret = el.selectionStart ?? d.caret);
		};
		const left = () => setTimeout(() => el.isConnected && note());
		const d = drafts.get(annotation.id);
		if (d?.open && d.focused) {
			el.focus({ preventScroll: true });
			el.setSelectionRange(d.caret, d.caret);
		}
		el.addEventListener('focus', note);
		el.addEventListener('input', note);
		el.addEventListener('keyup', note);
		el.addEventListener('pointerup', note);
		el.addEventListener('blur', left);
		return {
			destroy() {
				for (const [k, f] of [['focus', note], ['input', note], ['keyup', note], ['pointerup', note], ['blur', left]] as const) el.removeEventListener(k, f);
			}
		};
	}

	/** Close the form and forget what was written in it. */
	function cancel() {
		drafts.delete(annotation.id);
		open = null;
	}
	let row = $state<HTMLElement | undefined>();

	$effect(() => {
		for (const v of ENDPOINTS) can(v).then((ok) => (allowed[v] = ok));
	});

	const done = $derived(annotation.status !== 'open');
	const asks = $derived(staysOpen(store.manifest, annotation));
	const types = $derived(store.manifest?.annotation_types ?? []);
	const any = $derived(allowed.reply || allowed.edit || allowed.resolve || allowed.delete);

	function show(verb: Verb) {
		if (open === verb) return (open = null);
		// the block opens on what is there: what was being written for this verb, else an edit starts from the body it supersedes
		const d = drafts.get(annotation.id);
		const resume = d?.verb === verb;
		text = resume ? d.text : verb === 'edit' ? stripped(annotation.body_html) : '';
		type = resume ? d.type : (annotation.type ?? '');
		said = '';
		open = verb;
	}

	/** The body as text to edit. `body_html` is the published rendering; the source it came from is the Markdown a person typed. */
	function stripped(html: string): string {
		const el = document.createElement('div');
		el.innerHTML = html;
		return (el.textContent ?? '').trim();
	}

	async function send(endpoint: string, payload: Record<string, unknown>): Promise<boolean> {
		if (busy) return false;
		busy = true;
		said = '';
		const res = await write(endpoint, { annotation: annotation.id, ...payload });
		busy = false;
		if (res.ok) {
			drafts.delete(annotation.id);
			open = null;
			// the poll would find it within the second; refreshing now means the box changes as the button is released
			void store.refresh();
		} else {
			said = res.error?.message ?? 'the publisher refused it';
		}
		return res.ok;
	}

	const reply = () => text.trim() && send('reply', { message: text.trim() });
	// the type travels only when it changed, so an annotation whose type the quilt has since deleted can still be restated
	const edit = () => text.trim() && send('edit', { message: text.trim(), ...(type !== (annotation.type ?? '') ? { type } : {}) });
	/** Delete at once: the undo is what guards it, not a question first. */
	async function remove(): Promise<void> {
		if (busy) return;
		busy = true;
		said = await deleteAnnotation(annotation.id, store.manifest ? linkName(store.manifest, `quilt:${annotation.id}`) : 'an annotation');
		busy = false;
		if (!said) drafts.delete(annotation.id);
	}
	const resolve = () => send('resolve', {});
	const applied = () => send('resolve', { applied: true });
	const apply = () => send('suggestion-apply', {});
	const taken = $derived(annotation.change?.state === 'taken');
	const withText = $derived(annotation.payload !== null && annotation.payload !== undefined);
	const ready = $derived(annotation.change?.state === 'ready');
	const reopen = () => send('resolve', { undo: true });
</script>

{#if any}
	<span class="verbs" bind:this={row} data-testid="verb-row">
		{#if done}
			{#if allowed.resolve}
				<button type="button" class="verb" onclick={reopen} disabled={busy} data-testid="verb-reopen">reopen</button>
			{/if}
		{:else if compact}
			{#if allowed.edit}
				<button type="button" class="verb" onclick={() => show('edit')} aria-expanded={open === 'edit'} data-testid="verb-edit">edit</button>
			{/if}
		{:else}
			{#if allowed.reply}
				<button type="button" class="verb" onclick={() => show('reply')} aria-expanded={open === 'reply'} data-testid="verb-reply">reply</button>
			{/if}
			{#if allowed['suggestion-apply'] && ready}
				<button type="button" class="verb" onclick={apply} disabled={busy} title="Write its text into the file; a version of the document is kept first" data-testid="verb-apply">take it</button>
			{/if}
			{#if asks && allowed.resolve && taken}
				<button type="button" class="verb" onclick={applied} disabled={busy} title="The text now reads as this suggestion taken; its hash is recorded" data-testid="verb-applied">resolve as applied</button>
			{/if}
			{#if asks && allowed.resolve}
				<button type="button" class="verb" onclick={resolve} disabled={busy} data-testid="verb-resolve">{withText ? 'leave it' : 'resolve'}</button>
			{/if}
			{#if allowed.edit}
				<button type="button" class="verb" onclick={() => show('edit')} aria-expanded={open === 'edit'} data-testid="verb-edit">edit</button>
			{/if}
		{/if}
		{#if allowed.delete}
			<button type="button" class="verb" onclick={() => void remove()} disabled={busy} title="Take it and its replies out of the log; Undo puts them back" data-testid="verb-delete">delete</button>
		{/if}
	</span>
	{#if said && !open}
		<!-- a verb that opens nothing still shows why it was refused: "no author name…" is an answer the reader needs -->
		<p class="said" role="status" data-testid="verb-said">{said}</p>
	{/if}
	{#if open}
		<!-- beneath the meta line, inside the box: the box grows to hold it, and the words on the page stay where they are -->
		<div class="compose" data-testid="verb-panel">
			<textarea
				id="vp-{annotation.id}"
				rows={3}
				bind:value={text}
				use:track
				aria-label={open === 'reply' ? 'your reply' : 'restate the annotation'}
				placeholder={open === 'reply' ? 'reply' : ''}
				data-testid="verb-text"
			></textarea>
			<div class="row">
				{#if open === 'edit' && !compact}
					<span class="grow">
						<label for="vs-{annotation.id}">type</label>
						<select id="vs-{annotation.id}" bind:value={type} data-testid="verb-type">
							<option value="">No type</option>
							{#each types as t (t.id)}<option value={t.id}>{t.name}</option>{/each}
							{#if annotation.type && !types.some((t) => t.id === annotation.type)}<option value={annotation.type}>{annotation.type}</option>{/if}
						</select>
					</span>
				{/if}
				<button type="button" class="verb" onclick={cancel} data-testid="verb-cancel">cancel</button>
				{#if open === 'reply'}
					<button type="button" class="verb do" disabled={busy || !text.trim()} onclick={reply} data-testid="verb-send">reply</button>
				{:else}
					<button type="button" class="verb do" disabled={busy || !text.trim()} onclick={edit} data-testid="verb-send">save</button>
				{/if}
			</div>
			{#if said}<p class="said" role="status" data-testid="verb-said">{said}</p>{/if}
		</div>
	{/if}
{/if}

<svelte:window
	onpointerdown={(e) => {
		// a press inside the box is part of it; one landing outside closes what was being written
		if (open && !row?.closest('article.box')?.contains(e.target as Node)) open = null;
	}}
	onkeydown={(e) => e.key === 'Escape' && (open = null)}
/>

<style>
	.verbs {
		display: flex;
		gap: 10px;
		align-items: baseline;
		flex-wrap: wrap;
		margin-left: auto;
	}
	button.verb {
		font-family: var(--sans);
		font-size: inherit;
		background: none;
		border: 0;
		color: var(--ink-faint);
		padding: 0;
		cursor: pointer;
		line-height: inherit;
		white-space: nowrap;
	}
	button.verb:hover:not(:disabled),
	button.verb[aria-expanded='true'],
	button.verb.do {
		color: var(--ink-soft);
	}
	button.verb.do:hover:not(:disabled) {
		color: var(--ink);
	}
	button.verb:disabled {
		opacity: 0.4;
		cursor: default;
	}
	/* full width beneath the meta line, which wraps its children */
	.compose,
	.said {
		flex: 1 0 100%;
	}
	.compose {
		margin-top: var(--gap-tight);
		padding-top: var(--gap-tight);
		border-top: 1px solid var(--rule);
		display: grid;
		gap: var(--gap-hair);
	}
	.compose textarea,
	.compose select {
		font-family: var(--body-face);
		font-size: calc(var(--body-size) * 0.92);
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 3px;
		padding: 0.35em 0.5em;
		width: 100%;
		box-sizing: border-box;
		resize: vertical;
	}
	.compose select {
		font-family: var(--sans);
		font-size: inherit;
		width: auto;
	}
	.compose .row {
		display: flex;
		gap: 10px;
		align-items: center;
		justify-content: flex-end;
		flex-wrap: wrap;
	}
	.compose .row .grow {
		margin-right: auto;
		display: flex;
		gap: var(--gap-hair);
		align-items: center;
	}
	.said {
		margin: 0;
		color: var(--state-incomplete);
	}
</style>
