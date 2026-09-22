<script lang="ts">
	// What a person may do to a finding they are reading (plan 0.11 Part G's endpoints, given a surface at last).
	//
	// Loom serves six write endpoints and the viewer called two, so an annotation could be created and never answered: no reply, no resolution, no restatement, no withdrawal. These are the other four, as a row at the right of the box's header.
	//
	// The shape follows what each endpoint needs rather than one house style. `reply`, `edit` and `discard` take text, so each opens a small panel **above** the row — above, because a box in the gutter has the page to its left and the text below it, and a panel that pushed the body down would move the thing being discussed. `resolve` needs nothing, so it is one click, and the button that fired becomes its own undo where it stood: the row never changes length or order, so nothing moves under the pointer between the act and the second thoughts.
	//
	// In a gutter slot -- about 210px, `(container - measure) / 3` -- four verbs and the metadata cannot share a line, so `edit` and `discard` fold behind `⋯` and `reply` and `resolve` stay out. A container query, not a media query: the same box is wide inline and narrow in the gutter on one screen.
	import { can, known, write } from '$lib/write';
	import { store } from '$lib/manifest/client.svelte';
	import type { Annotation } from '$lib/manifest/types';

	let {
		annotation,
		compact = false
	}: {
		annotation: Annotation;
		/** A reply's own row: withdrawal only, and no panel of its own to nest inside its parent's. */
		compact?: boolean;
	} = $props();

	type Verb = 'reply' | 'edit' | 'discard';

	//: Seeded from the probe's standing answer, so a row re-mounted after a write does not blink out while it asks again.
	const VERBS = ['reply', 'edit', 'resolve', 'discard'];
	let allowed = $state<Record<string, boolean>>(
		Object.fromEntries(VERBS.map((v) => [v, known(v) ?? false]).filter(([, ok]) => ok))
	);
	let open = $state<Verb | null>(null);
	let menu = $state(false);
	let busy = $state(false);
	let said = $state('');
	let text = $state('');
	let severity = $state('');

	$effect(() => {
		for (const v of VERBS) can(v).then((ok) => (allowed[v] = ok));
	});

	const resolved = $derived(annotation.status === 'resolved');
	const gone = $derived(annotation.status === 'discarded' || annotation.discarded);
	const any = $derived(allowed.reply || allowed.edit || allowed.resolve || allowed.discard);

	function show(verb: Verb) {
		menu = false;
		if (open === verb) return (open = null);
		// the panel opens on what is there: an edit starts from the body it supersedes
		text = verb === 'edit' ? stripped(annotation.body_html) : '';
		severity = verb === 'edit' ? (annotation.severity ?? '') : '';
		said = '';
		open = verb;
	}

	/** The body as text to edit. `body_html` is the published rendering; the source it came from is the Markdown a person typed. */
	function stripped(html: string): string {
		const el = document.createElement('div');
		el.innerHTML = html;
		return (el.textContent ?? '').trim();
	}

	async function send(endpoint: string, payload: Record<string, unknown>) {
		if (busy) return;
		busy = true;
		said = '';
		const res = await write(endpoint, { annotation: annotation.id, ...payload });
		busy = false;
		if (res.ok) {
			open = null;
			menu = false;
			// the poll would find it within the second; refreshing now means the box changes as the button is released
			void store.refresh();
		} else {
			said = res.error?.message ?? 'the publisher refused it';
		}
	}

	const reply = () => text.trim() && send('reply', { message: text.trim() });
	const edit = () => text.trim() && send('edit', { message: text.trim(), severity: severity || undefined });
	const discard = () => send('discard', { reason: text.trim() || undefined });
	const resolve = () => send('resolve', {});
	const undo = (endpoint: 'resolve' | 'discard') => send(endpoint, { undo: true });
</script>

{#if any}
	<div class="verbs" class:compact data-testid="verb-row">
		{#if said && !open}
			<!-- `resolve` needs no panel, so its refusal had nowhere to be shown and was dropped: the reader clicked,
			     nothing happened, and the publisher's reason — "no author name…" — never reached them. -->
			<p class="said bare" role="status" data-testid="verb-said">{said}</p>
		{/if}
		{#if open}
			<!-- above the row: the body below it is what the panel is about, and must not move -->
			<div class="pop" data-testid="verb-panel">
				<label for="vp-{annotation.id}">
					{open === 'reply' ? 'your reply' : open === 'edit' ? 'restate the finding' : 'why this should not have stood'}
				</label>
				<textarea
					id="vp-{annotation.id}"
					rows={open === 'discard' ? 2 : 3}
					bind:value={text}
					placeholder={open === 'discard' ? 'optional — published as the reason it was withdrawn' : ''}
					data-testid="verb-text"
				></textarea>
				<div class="row">
					{#if open === 'edit'}
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
					<button type="button" class="ghost" onclick={() => (open = null)}>Cancel</button>
					{#if open === 'reply'}
						<button type="button" class="primary" disabled={busy || !text.trim()} onclick={reply} data-testid="verb-send">Reply</button>
					{:else if open === 'edit'}
						<button type="button" class="primary" disabled={busy || !text.trim()} onclick={edit} data-testid="verb-send">Save</button>
					{:else}
						<button type="button" class="primary danger" disabled={busy} onclick={discard} data-testid="verb-send">Discard</button>
					{/if}
				</div>
				{#if said}<p class="said" role="status" data-testid="verb-said">{said}</p>{/if}
			</div>
		{/if}

		{#if gone}
			{#if allowed.discard}
				<button type="button" class="verb undo" onclick={() => undo('discard')} disabled={busy} data-testid="verb-undo-discard">undo discard</button>
			{/if}
		{:else if compact}
			{#if allowed.discard}
				<button type="button" class="verb danger" onclick={() => show('discard')} aria-expanded={open === 'discard'} data-testid="verb-discard">discard</button>
			{/if}
		{:else}
			{#if allowed.reply}
				<button type="button" class="verb" onclick={() => show('reply')} aria-expanded={open === 'reply'} data-testid="verb-reply">reply</button>
			{/if}
			{#if allowed.resolve}
				{#if resolved}
					<button type="button" class="verb undo" onclick={() => undo('resolve')} disabled={busy} data-testid="verb-undo-resolve">undo resolve</button>
				{:else}
					<button type="button" class="verb" onclick={resolve} disabled={busy} data-testid="verb-resolve">resolve</button>
				{/if}
			{/if}
			<!-- wide: edit and discard stand beside the others. narrow: they fold behind the menu below. -->
			{#if allowed.edit}
				<button type="button" class="verb wide-only" onclick={() => show('edit')} aria-expanded={open === 'edit'} data-testid="verb-edit">edit</button>
			{/if}
			{#if allowed.discard}
				<button type="button" class="verb danger wide-only" onclick={() => show('discard')} aria-expanded={open === 'discard'} data-testid="verb-discard">discard</button>
			{/if}
			{#if allowed.edit || allowed.discard}
				<span class="more narrow-only">
					<button type="button" class="verb" onclick={() => (menu = !menu)} aria-haspopup="true" aria-expanded={menu} aria-label="more actions" data-testid="verb-more">⋯</button>
					{#if menu}
						<span class="menu" data-testid="verb-menu">
							{#if allowed.edit}<button type="button" onclick={() => show('edit')}>Edit the finding</button>{/if}
							{#if allowed.discard}<button type="button" class="danger" onclick={() => show('discard')}>Discard it</button>{/if}
						</span>
					{/if}
				</span>
			{/if}
		{/if}
	</div>
{/if}

<svelte:window
	onpointerdown={(e) => {
		// a click inside the row or its panel is part of it; only one landing outside dismisses
		if (!(e.target as Element | null)?.closest?.('[data-testid="verb-row"]')) {
			open = null;
			menu = false;
		}
	}}
	onkeydown={(e) => e.key === 'Escape' && ((open = null), (menu = false))}
/>

<style>
	.verbs {
		display: flex;
		gap: 2px;
		align-items: center;
		position: relative;
		flex-wrap: wrap;
	}
	button.verb {
		font-family: var(--sans);
		font-size: 0.85em;
		background: none;
		border: 1px solid transparent;
		color: var(--ink-faint);
		border-radius: var(--rad-control);
		padding: 0.1em 0.5em;
		cursor: pointer;
		line-height: 1.5;
		white-space: nowrap;
	}
	.compact button.verb {
		font-size: 0.78em;
	}
	button.verb:hover:not(:disabled),
	button.verb[aria-expanded='true'] {
		color: var(--ink);
		background: var(--sheet);
		border-color: var(--rule);
	}
	button.verb.danger:hover:not(:disabled) {
		color: var(--state-incomplete);
		border-color: var(--state-incomplete);
	}
	button.verb.undo {
		color: var(--link);
	}
	button.verb:disabled {
		opacity: 0.4;
		cursor: default;
	}

	/* The panel sits above the row so the body it is about never moves. */
	.pop {
		position: absolute;
		bottom: calc(100% + var(--gap-hair));
		right: 0;
		width: min(23rem, 74vw);
		background: var(--sheet);
		border: 1px solid var(--rule-strong);
		border-radius: var(--rad-control);
		box-shadow: 0 6px 20px rgb(0 0 0 / 16%);
		padding: var(--gap-tight);
		z-index: 40;
		display: grid;
		gap: var(--gap-hair);
		text-align: left;
	}
	.pop label {
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
	}
	.pop textarea,
	.pop select {
		font-family: var(--sans);
		font-size: 0.9em;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 0.35em 0.45em;
		width: 100%;
		resize: vertical;
	}
	.pop .row {
		display: flex;
		gap: var(--gap-hair);
		align-items: center;
		justify-content: flex-end;
		flex-wrap: wrap;
	}
	.pop .row .grow {
		margin-right: auto;
		display: flex;
		gap: var(--gap-hair);
		align-items: center;
	}
	.said.bare {
		margin: 0 0 var(--gap-hair);
		font-size: 0.9em;
		color: var(--state-incomplete, #c4583c);
	}
	.pop .said {
		margin: 0;
		font-size: 0.85em;
		color: var(--state-incomplete);
	}
	button.primary,
	button.ghost {
		font-family: var(--sans);
		font-size: 0.85em;
		border-radius: var(--rad-control);
		padding: 0.25em 0.7em;
		cursor: pointer;
	}
	button.primary {
		background: var(--ink);
		color: var(--paper);
		border: 1px solid var(--ink);
	}
	button.primary.danger {
		background: var(--state-incomplete);
		border-color: var(--state-incomplete);
		color: var(--paper);
	}
	button.ghost {
		background: none;
		color: var(--ink-soft);
		border: 1px solid var(--rule);
	}
	button:disabled {
		opacity: 0.5;
		cursor: default;
	}

	.more {
		position: relative;
	}
	.menu {
		position: absolute;
		right: 0;
		top: calc(100% + var(--gap-hair));
		background: var(--sheet);
		border: 1px solid var(--rule-strong);
		border-radius: var(--rad-control);
		box-shadow: 0 6px 20px rgb(0 0 0 / 16%);
		display: grid;
		min-width: 9rem;
		z-index: 40;
		overflow: hidden;
	}
	.menu button {
		font-family: var(--sans);
		font-size: 0.85em;
		background: none;
		border: none;
		text-align: left;
		padding: 0.4em 0.7em;
		color: var(--ink);
		cursor: pointer;
	}
	.menu button:hover {
		background: var(--leaf);
	}
	.menu button.danger {
		color: var(--state-incomplete);
	}

	/* A gutter slot is about 210px. Four verbs and the metadata cannot share that line, so two fold behind `⋯`. */
	.narrow-only {
		display: none;
	}
	@container annotation (max-width: 330px) {
		.wide-only {
			display: none;
		}
		.narrow-only {
			display: inline-block;
		}
	}
</style>
