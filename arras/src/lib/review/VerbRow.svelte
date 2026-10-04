<script lang="ts">
	// The verbs an annotation offers (book 15.3.4a), as one quiet row at the right of its box's meta line, and the place a reply, a restatement or a reason is written: a block that opens inside the box beneath the meta line, so nothing an annotation can do happens outside its box. Each verb is shown only when `GET /_api` says the publisher serves its endpoint.
	//
	// An open annotation offers reply, resolve, edit and withdraw (the `discard` endpoint); a citation offers accept and reject in place of resolve and edit, since a citation is answered by deciding it. A settled one offers `reopen` alone, the undo of whichever of resolve or withdraw settled it. A reply's own row (`compact`) is edit and withdraw.
	import { untrack } from 'svelte';
	import { can, known, write } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import { decided } from './decisions.svelte';
	import { drafts, type Verb } from './drafts';
	import type { Annotation } from '$lib/manifest/types';

	let {
		annotation,
		compact = false
	}: {
		annotation: Annotation;
		/** A reply's own row: edit and withdraw. */
		compact?: boolean;
	} = $props();

	//: Seeded from the probe's standing answer, so a row re-mounted after a write does not blink out while it asks again.
	const ENDPOINTS = ['reply', 'edit', 'resolve', 'discard', 'library-cite'];
	let allowed = $state<Record<string, boolean>>(
		Object.fromEntries(ENDPOINTS.map((v) => [v, known(v) ?? false]).filter(([, ok]) => ok))
	);
	// a box made again -- which happens whenever a new manifest arrives -- opens on what was being written in it
	const kept = untrack(() => drafts.get(annotation.id));
	let open = $state<Verb | null>(kept?.open ? kept.verb : null);
	let busy = $state(false);
	let said = $state('');
	let text = $state(kept?.text ?? '');
	let severity = $state(kept?.severity ?? '');

	$effect(() => {
		const verb = open;
		const now = { text, severity };
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

	const gone = $derived(annotation.status === 'discarded' || annotation.discarded);
	const done = $derived(gone || annotation.status !== 'open');
	const citation = $derived(annotation.kind === 'citation' && !compact);
	const any = $derived(allowed.reply || allowed.edit || allowed.resolve || allowed.discard || allowed['library-cite']);

	function show(verb: Verb) {
		if (open === verb) return (open = null);
		// the block opens on what is there: what was being written for this verb, else an edit starts from the body it supersedes
		const d = drafts.get(annotation.id);
		const resume = d?.verb === verb;
		text = resume ? d.text : verb === 'edit' ? stripped(annotation.body_html) : '';
		severity = resume ? d.severity : verb === 'edit' ? (annotation.severity ?? '') : '';
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
	const edit = () => text.trim() && send('edit', { message: text.trim(), severity: severity || undefined });
	const discard = () => send('discard', { reason: text.trim() || undefined });
	const resolve = () => send('resolve', {});
	const reopen = () => send(gone ? 'discard' : 'resolve', { undo: true });
	const decide = async (decision: 'accept' | 'reject') => {
		if (await send('library-cite', { decision })) decided[annotation.id] = decision === 'accept' ? 'accepted' : 'rejected';
	};
</script>

{#if any}
	<span class="verbs" bind:this={row} data-testid="verb-row">
		{#if done}
			{#if allowed[gone ? 'discard' : 'resolve']}
				<button type="button" class="verb" onclick={reopen} disabled={busy} data-testid="verb-reopen">reopen</button>
			{/if}
		{:else if compact}
			{#if allowed.edit}
				<button type="button" class="verb" onclick={() => show('edit')} aria-expanded={open === 'edit'} data-testid="verb-edit">edit</button>
			{/if}
			{#if allowed.discard}
				<button type="button" class="verb" onclick={() => show('discard')} aria-expanded={open === 'discard'} data-testid="verb-withdraw">withdraw</button>
			{/if}
		{:else}
			{#if citation && allowed['library-cite']}
				<button type="button" class="verb" onclick={() => decide('accept')} disabled={busy} data-testid="verb-accept">accept</button>
				<button type="button" class="verb" onclick={() => decide('reject')} disabled={busy} data-testid="verb-reject">reject</button>
			{/if}
			{#if allowed.reply}
				<button type="button" class="verb" onclick={() => show('reply')} aria-expanded={open === 'reply'} data-testid="verb-reply">reply</button>
			{/if}
			{#if !citation && allowed.resolve}
				<button type="button" class="verb" onclick={resolve} disabled={busy} data-testid="verb-resolve">resolve</button>
			{/if}
			{#if !citation && allowed.edit}
				<button type="button" class="verb" onclick={() => show('edit')} aria-expanded={open === 'edit'} data-testid="verb-edit">edit</button>
			{/if}
			{#if allowed.discard}
				<button type="button" class="verb" onclick={() => show('discard')} aria-expanded={open === 'discard'} data-testid="verb-discard">withdraw</button>
			{/if}
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
				rows={open === 'discard' ? 2 : 3}
				bind:value={text}
				use:track
				aria-label={open === 'reply' ? 'your reply' : open === 'edit' ? 'restate the annotation' : 'why it should not have stood'}
				placeholder={open === 'reply' ? 'reply' : open === 'discard' ? 'why, optionally — published as the reason' : ''}
				data-testid="verb-text"
			></textarea>
			<div class="row">
				{#if open === 'edit' && !compact}
					<span class="grow">
						<label for="vs-{annotation.id}">severity</label>
						<select id="vs-{annotation.id}" bind:value={severity} data-testid="verb-severity">
							<option value="">none</option>
							<option value="major">major</option>
							<option value="moderate">moderate</option>
							<option value="minor">minor</option>
						</select>
					</span>
				{/if}
				<button type="button" class="verb" onclick={cancel} data-testid="verb-cancel">cancel</button>
				{#if open === 'reply'}
					<button type="button" class="verb do" disabled={busy || !text.trim()} onclick={reply} data-testid="verb-send">reply</button>
				{:else if open === 'edit'}
					<button type="button" class="verb do" disabled={busy || !text.trim()} onclick={edit} data-testid="verb-send">save</button>
				{:else}
					<button type="button" class="verb do" disabled={busy} onclick={discard} data-testid="verb-send">withdraw</button>
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
		color: var(--ann-objection);
	}
</style>
