<script lang="ts">
	// A proposed digest node, met in place while browsing (plan 0.12 §5.2, §5.3).
	//
	// **Both texts, always.** The page's own words beside the LaTeX an agent rendered them into: the entire claim being made is that these two say the same thing, and a surface that offers `verify` without showing both is a bug rather than a shortcut. That is the one non-negotiable in this design.
	//
	// Three routes, not two. The common failure is a rendering that is slightly off, not one that is wrong, so `edit` opens the LaTeX for correction and verifies the author's own text. What is edited is `statement`; `source_text` and the anchor it names are untouched, so an edited node stays re-checkable -- and the provenance records both parties, because a record that credits an agent with a sentence a person wrote cannot be audited.
	import { can, write } from '$lib/write';
	import { dataUrl } from '$lib/paths';
	import { store } from '$lib/manifest/client.svelte';
	import Statement from '$lib/math/Statement.svelte';
	import type { ResultRecord } from '$lib/manifest/types';

	let {
		id,
		record,
		citekey
	}: {
		id: string;
		record: ResultRecord;
		citekey: string;
	} = $props();

	let allowed = $state(false);
	let open = $state<'edit' | 'discard' | null>(null);
	let busy = $state(false);
	let said = $state('');
	let text = $state('');
	let name = $state('');
	let pagesEl: HTMLElement | undefined = $state();

	/** Open the page at the quotation rather than at the top: page 1 of a paper is its masthead, and the formula being judged was below the fold. */
	function focusPage() {
		const img = pagesEl?.querySelector('img');
		if (record.page_focus == null || !pagesEl || !img || !img.clientHeight) return;
		pagesEl.scrollTop = Math.max(0, record.page_focus * img.clientHeight - 32);
	}

	// An image from the cache can finish loading before an `onload` is attached, so a load handler alone is not a
	// trigger that can be relied on: scroll now if the image is complete, else when it loads.
	$effect(() => {
		const img = pagesEl?.querySelector('img');
		if (!img) return;
		if (img.complete) focusPage();
		else img.addEventListener('load', focusPage, { once: true });
		return () => img.removeEventListener('load', focusPage);
	});

	$effect(() => {
		void can('digest-verify').then((ok) => (allowed = ok));
	});

	const proposer = $derived(record.origin.find((o) => o.act === 'proposed')?.by || 'an agent');

	function panel(which: 'edit' | 'discard') {
		said = '';
		if (open === which) return (open = null);
		text = which === 'edit' ? (record.statement ?? '') : '';
		name = record.local ?? '';
		open = which;
	}

	async function send(endpoint: string, body: Record<string, unknown>) {
		if (busy) return;
		busy = true;
		said = '';
		const res = await write(endpoint, { node: id, ...body });
		busy = false;
		if (res.ok) {
			open = null;
			void store.refresh();
		} else {
			said = res.error?.message ?? 'the publisher refused it';
		}
	}

	/** The page text split around the quoted span, so the quote can be marked; whitespace-insensitive, since the quote was normalised. */
	function marked(page: string, quote: string): { text: string; hit: boolean }[] {
		const words = quote.trim().split(/\s+/).filter(Boolean);
		if (!words.length) return [{ text: page, hit: false }];
		const pattern = new RegExp(words.slice(0, 8).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+'));
		const m = pattern.exec(page);
		if (!m) return [{ text: page, hit: false }];
		return [
			{ text: page.slice(0, m.index), hit: false },
			{ text: m[0], hit: true },
			{ text: page.slice(m.index + m[0].length), hit: false }
		];
	}

	const verify = () => send('digest-verify', {});
	/** Edit-then-verify: the rendering, the name, or both -- only what the author changed is sent. */
	function verifyEdited() {
		const body: Record<string, unknown> = {};
		if (text.trim() && text.trim() !== (record.statement ?? '').trim()) body.statement = text.trim();
		if (name.trim() && name.trim() !== (record.local ?? '')) body.local = name.trim();
		return send('digest-verify', body);
	}
	const discard = () => text.trim() && send('digest-discard', { reason: text.trim() });
</script>

<article class="proposal" data-testid="proposal" data-id={id}>
	<header>
		<span class="flag" data-testid="proposal-flag">proposed</span>
		<code class="id">{id}</code>
		<span class="where">
			{#if record.page}p.{record.page} of <code>{record.artifact}</code>{:else}<code>{record.source_file ?? 'the source'}</code>{/if}
			· level {record.level} · read by {proposer}
		</span>
	</header>

	<!-- The two texts, side by side. Neither is decoration: the left is what the page says and the right is a claim about it. -->
	<div class="texts">
		<section class="side" data-testid="proposal-source">
			<h4>{record.page ? 'the page says' : 'the source says'}</h4>
			{#if record.page_text}
				<!-- the page around the quote, with the quote marked: an agent quotes only what the anchor needs, and a
				     rendering cannot be judged against the one clause that passed the check -->
				<p class="verbatim" data-testid="proposal-page">{#each marked(record.page_text, record.source_text ?? '') as part, i (i)}{#if part.hit}<mark>{part.text}</mark>{:else}{part.text}{/if}{/each}</p>
			{:else}
				<p class="verbatim">{record.source_text}</p>
			{/if}
		</section>
		<section class="side" data-testid="proposal-statement">
			<h4>rendered as</h4>
			<p class="rendered"><Statement text={record.statement ?? ''} /></p>
		</section>
	</div>

	{#if record.not_on_page?.length}
		<!-- words the rendering has and the quote does not: in the third study run an author comparing thirteen statements by eye let one such gloss through -->
		<p class="added" data-testid="proposal-added">
			not in the quoted page text:
			{#each record.not_on_page as word (word)}<code>{word}</code>{' '}{/each}
		</p>
	{/if}

	{#if record.page_images?.length}
		<!-- the page itself: the text layer keeps "X" for both a stack and its space, and a hypothesis moved from one to the other passed every text check -->
		<details class="image" open data-testid="proposal-image">
			<summary>the page itself <span class="why">— judge symbols here; the text above has lost script, bold and indices</span></summary>
			<div class="pages" bind:this={pagesEl}>
				{#each record.page_images as src, i (src)}
					<div class="sheet">
						<img src={dataUrl(src)} alt="page {record.page + i} of {citekey}" />
						{#if i === 0 && record.page_focus != null}
							<span class="marker" style="top: {record.page_focus * 100}%" data-testid="proposal-focus" aria-hidden="true"></span>
						{/if}
					</div>
				{/each}
			</div>
		</details>
	{:else if record.page_text && record.page}
		<p class="noimage" data-testid="proposal-noimage">no page image: the PDF is not on the machine that built this, so symbols can be judged only from the text</p>
	{/if}

	{#if open}
		<div class="pop" data-testid="proposal-panel">
			<label for="pp-{id}">{open === 'edit' ? 'your rendering — the page text and the anchor are untouched' : 'why this should not stand'}</label>
			<textarea id="pp-{id}" rows={open === 'edit' ? 4 : 2} bind:value={text} data-testid="proposal-text"></textarea>
			{#if open === 'edit'}
				<!-- the paper's own name for it: an agent called Brion's Corollary 3.2.1 "Theorem 3.2", and the author could fix the text but not the name -->
				<label for="pn-{id}">the paper's name for it</label>
				<input id="pn-{id}" class="name" bind:value={name} data-testid="proposal-name" />
			{/if}
			<div class="row">
				<button type="button" class="ghost" onclick={() => (open = null)}>Cancel</button>
				{#if open === 'edit'}
					<button type="button" class="primary" disabled={busy || !text.trim()} onclick={verifyEdited} data-testid="proposal-send">Verify as edited</button>
				{:else}
					<button type="button" class="primary danger" disabled={busy || !text.trim()} onclick={discard} data-testid="proposal-send">Discard</button>
				{/if}
			</div>
			{#if said}<p class="said" role="status" data-testid="proposal-said">{said}</p>{/if}
		</div>
	{/if}

	{#if allowed}
		<footer class="verbs">
			<button type="button" class="verb" onclick={verify} disabled={busy} data-testid="proposal-verify">verify</button>
			<button type="button" class="verb" onclick={() => panel('edit')} aria-expanded={open === 'edit'} data-testid="proposal-edit">edit</button>
			<button type="button" class="verb danger" onclick={() => panel('discard')} aria-expanded={open === 'discard'} data-testid="proposal-discard">discard</button>
			<span class="hint">{citekey}</span>
		</footer>
	{:else}
		<footer class="verbs"><span class="hint">read-only: this corpus is published, not served</span></footer>
	{/if}
</article>

<style>
	.proposal {
		border: 1px solid var(--rule-strong);
		border-left: 3px solid var(--state-proposed, var(--link));
		border-radius: var(--rad-control);
		padding: var(--gap-tight);
		margin: var(--gap) 0;
		background: var(--sheet);
		container: proposal / inline-size;
	}
	header {
		display: flex;
		gap: var(--gap-hair);
		align-items: baseline;
		flex-wrap: wrap;
		font-size: 0.85em;
	}
	.flag {
		font-family: var(--sans);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		font-size: 0.78em;
		color: var(--link);
		border: 1px solid var(--link);
		border-radius: var(--rad-control);
		padding: 0 0.4em;
	}
	.where {
		color: var(--ink-faint);
		margin-left: auto;
	}
	.texts {
		display: grid;
		gap: var(--gap-tight);
		grid-template-columns: 1fr;
		margin-top: var(--gap-tight);
	}
	@container proposal (min-width: 620px) {
		.texts {
			grid-template-columns: 1fr 1fr;
		}
	}
	.side h4 {
		margin: 0 0 0.25em;
		font-family: var(--sans);
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
		font-weight: 500;
	}
	.verbatim {
		margin: 0;
		font-family: var(--mono);
		font-size: 0.82em;
		line-height: 1.5;
		white-space: pre-wrap;
		color: var(--ink-soft);
	}
	.verbatim mark {
		background: var(--leaf);
		color: var(--ink);
		border-bottom: 1px solid var(--link);
	}
	.rendered {
		margin: 0;
		line-height: 1.5;
	}
	.added {
		margin: var(--gap-hair) 0 0;
		font-size: 0.82em;
		color: var(--state-stale, var(--ink-soft));
	}
	.added code {
		font-size: 0.95em;
		border-bottom: 1px dotted currentColor;
	}
	.image {
		margin-top: var(--gap-tight);
	}
	.image summary {
		cursor: pointer;
		font-family: var(--sans);
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
	}
	.image .why {
		text-transform: none;
		letter-spacing: 0;
	}
	.pages {
		max-height: 70vh;
		overflow: auto;
		margin-top: var(--gap-hair);
		border: 1px solid var(--rule);
		background: var(--sheet);
	}
	.sheet {
		position: relative;
	}
	.pages img {
		display: block;
		max-width: 100%;
	}
	/* where the quotation starts, in the margin: the image cannot be marked up, so the eye is led to the line */
	.marker {
		position: absolute;
		left: 0;
		width: 4px;
		height: 3em;
		background: var(--link);
		border-radius: 0 2px 2px 0;
	}
	.noimage {
		margin: var(--gap-hair) 0 0;
		font-size: 0.78em;
		color: var(--ink-faint);
	}
	.verbs {
		display: flex;
		gap: 2px;
		align-items: center;
		margin-top: var(--gap-tight);
		border-top: 1px solid var(--rule);
		padding-top: var(--gap-hair);
	}
	.hint {
		margin-left: auto;
		font-size: 0.78em;
		color: var(--ink-faint);
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
	}
	button.verb:hover:not(:disabled),
	button.verb[aria-expanded='true'] {
		color: var(--ink);
		background: var(--leaf);
		border-color: var(--rule);
	}
	button.verb.danger:hover:not(:disabled) {
		color: var(--state-incomplete);
		border-color: var(--state-incomplete);
	}
	.pop {
		display: grid;
		gap: var(--gap-hair);
		margin-top: var(--gap-tight);
	}
	.pop label {
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
	}
	.pop textarea {
		font-family: var(--mono);
		font-size: 0.85em;
		color: var(--ink);
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 0.4em;
		width: 100%;
		box-sizing: border-box;
		resize: vertical;
	}
	.pop input.name {
		font-family: var(--mono);
		font-size: 0.85em;
		color: var(--ink);
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 0.25em 0.4em;
		max-width: 20em;
	}
	.pop .row {
		display: flex;
		gap: var(--gap-hair);
		justify-content: flex-end;
	}
	.said {
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
</style>
