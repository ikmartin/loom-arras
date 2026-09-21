<script lang="ts">
	// A proposed digest node, met in place while browsing (plan 0.12 §5.2, §5.3).
	//
	// **Both texts, always.** The page's own words beside the LaTeX an agent rendered them into: the entire claim being made is that these two say the same thing, and a surface that offers `verify` without showing both is a bug rather than a shortcut. That is the one non-negotiable in this design.
	//
	// Three routes, not two. The common failure is a rendering that is slightly off, not one that is wrong, so `edit` opens the LaTeX for correction and verifies the author's own text. What is edited is `statement`; `source_text` and the anchor it names are untouched, so an edited node stays re-checkable -- and the provenance records both parties, because a record that credits an agent with a sentence a person wrote cannot be audited.
	import { can, write } from '$lib/write';
	import { artifactUrl, dataUrl } from '$lib/paths';
	import { store } from '$lib/manifest/client.svelte';
	import Statement from '$lib/math/Statement.svelte';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';
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
	/** The work this proposal is about, for the paper itself and the geometry of its anchor. */
	const ref = $derived(store.manifest?.references?.[citekey]);
	const paper = $derived(ref?.artifacts?.pdf ? artifactUrl(ref.artifacts.dir) : '');

	interface Sidecar {
		quads: Record<string, number[][]>;
	}
	let spans = $state<Sidecar | null>(null);

	// Fetched by the sidecar's own hash, not derived from the manifest: the manifest is replaced on every poll, and a
	// box that re-fetched geometry once a second would re-render the page it is asking the author to read.
	$effect(() => {
		const at = ref?.spans;
		if (!at || !paper) return;
		let dropped = false;
		fetch(dataUrl(at.path))
			.then((r) => (r.ok ? (r.json() as Promise<Sidecar>) : null))
			.then((j) => {
				if (!dropped) spans = j;
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	/** The quotation's own rectangles, so the page opens at it rather than at the masthead. */
	const quoted = $derived(
		(spans?.quads?.[id] ?? []).length ? [{ id, page: record.page, rects: spans!.quads[id] }] : []
	);

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

	<!-- The page itself beside the rendering. Neither is decoration: the left is the document and the right is a claim
	     about it, and a surface that offers `verify` without showing both is a bug rather than a shortcut. The text
	     layer keeps one "X" for both a stack and its coarse space, and a hypothesis that moved between them passed
	     every text check loom has (DR-179) — which is why the page, and not only its text, is what is shown. -->
	<div class="texts">
		<section class="side" data-testid="proposal-source">
			<h4>{record.page ? 'the page says' : 'the source says'}</h4>
			{#if paper && record.page}
				<div class="paper" data-testid="proposal-paper">
					<PdfDoc url={paper} page={record.page} spans={quoted} focus={id} scale={1.1} window={0} toolbar={false} />
				</div>
			{:else if record.page_text}
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

	{#if paper && record.page && record.page_text}
		<!-- the page's own words, which is what the anchor check runs against; the page above is what settles a symbol -->
		<details class="pagetext" data-testid="proposal-pagetext">
			<summary>the page's text <span class="why">— what the anchor is checked against, with the quotation marked</span></summary>
			<p class="verbatim" data-testid="proposal-page">{#each marked(record.page_text, record.source_text ?? '') as part, i (i)}{#if part.hit}<mark>{part.text}</mark>{:else}{part.text}{/if}{/each}</p>
		</details>
	{/if}

	{#if record.not_on_page?.length}
		<!-- words the rendering has and the quote does not: in the third study run an author comparing thirteen statements by eye let one such gloss through -->
		<p class="added" data-testid="proposal-added">
			not in the quoted page text:
			{#each record.not_on_page as word (word)}<code>{word}</code>{' '}{/each}
		</p>
	{/if}

	{#if !paper && record.page_text && record.page}
		<p class="noimage" data-testid="proposal-noimage">
			no copy of the paper on this machine, so symbols can be judged only from the text above
		</p>
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
	.paper {
		height: 46vh;
		min-height: 260px;
		border: 1px solid var(--rule);
		background: var(--sheet);
	}
	.pagetext {
		margin-top: var(--gap-tight);
	}
	.pagetext summary {
		cursor: pointer;
		font-family: var(--sans);
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
	}
	.pagetext .why {
		text-transform: none;
		letter-spacing: 0;
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
