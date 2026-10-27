<script lang="ts">
	// One proposed result, judged at full width (WQ-55): its name, then the paper's words — the page cropped to the statement where the sidecar knows where it is, else the page's text with the quote marked — and beneath them, at the same width, the rendering the publisher made of the proposal, its words the page does not have marked. Verify, edit and discard stand directly under what they judge, with keys; discard asks its one-line reason here, since it is what `loom library propose` tells the next agent that proposes the same result.
	//
	// **Both texts, always.** The page's own words and the LaTeX an agent rendered them into: the claim being made is that these two say the same thing, and a surface that offers verify without showing both is a bug rather than a shortcut. An edit corrects the rendering (and the paper's name for it) and verifies the author's own text; the quote and the anchor it names are untouched.
	import { untrack } from 'svelte';
	import { write } from '$lib/write';
	import { artifactUrl, dataUrl } from '$lib/paths';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import Statement from '$lib/math/Statement.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';
	import { bibText, surnames } from '$lib/works';
	import type { ResultRecord } from '$lib/manifest/types';

	let {
		id,
		record,
		citekey,
		writable,
		onacted
	}: {
		id: string;
		record: ResultRecord;
		citekey: string;
		/** Whether the publisher serves the verbs. */
		writable: boolean;
		/** Told once a verb was taken, so the queue can move to the next. */
		onacted: () => void;
	} = $props();

	const m = $derived(store.manifest!);
	const ref = $derived(m.references?.[citekey]);
	const node = $derived(m.nodes[id]);
	const paper = $derived(ref?.artifacts?.pdf ? artifactUrl(ref.artifacts.dir) : '');
	// "Definition 2.3", the paper's own name for it, from the node's locator (`Definition 2.3, p.~7`)
	const named = $derived((node?.locator ?? '').split(',')[0].replace(/~/g, ' ').trim() || record.local || id);
	const proposer = $derived((record.origin ?? []).find((o) => o.act === 'proposed')?.by || 'an agent');

	interface Sidecar {
		quads: Record<string, number[][]>;
	}
	let spans = $state<Sidecar | null>(null);
	// fetched by the sidecar's own path, not derived from the manifest: the manifest is replaced on every poll, and a card that re-fetched geometry once a second would draw the page it asks the author to read again and again
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
	const rects = $derived(spans?.quads?.[id] ?? []);

	// the page drawn the card's width, and cropped to the statement and two lines either side
	const PAGE_WIDTH = 612;
	let width = $state(0);
	const scale = $derived(width ? width / PAGE_WIDTH : 1);
	const crop = $derived.by(() => {
		if (!rects.length) return 0;
		const top = Math.min(...rects.map((r) => r[1]));
		const bottom = Math.max(...rects.map((r) => r[3]));
		const line = Math.max(...rects.map((r) => r[3] - r[1]));
		return Math.round((bottom - top + line * 4) * scale);
	});

	/** The page text split round the quote, so the quote can be marked; whitespace-insensitive, since the quote was normalised. */
	function marked(page: string, quote: string): { text: string; hit: boolean }[] {
		const words = quote.trim().split(/\s+/).filter(Boolean);
		if (!words.length) return [{ text: page, hit: false }];
		const pattern = new RegExp(words.slice(0, 8).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('\\s+'));
		const hit = pattern.exec(page);
		if (!hit) return [{ text: page, hit: false }];
		return [
			{ text: page.slice(0, hit.index), hit: false },
			{ text: hit[0], hit: true },
			{ text: page.slice(hit.index + hit[0].length), hit: false }
		];
	}

	/** Mark, in the rendering, each word the page does not have, as compare marks a changed word; mathematics is left alone, since the words compared are the prose's. */
	function markWords(root: HTMLElement): void {
		const words = record.not_on_page ?? [];
		if (!words.length) return;
		const pattern = new RegExp(`\\b(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'gi');
		const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
			acceptNode: (n) => (n.parentElement?.closest('.math, mjx-container, mark.review-changed') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT)
		});
		const texts: Text[] = [];
		for (let n = walk.nextNode(); n; n = walk.nextNode()) texts.push(n as Text);
		for (const t of texts) {
			const value = t.nodeValue ?? '';
			pattern.lastIndex = 0;
			if (!pattern.test(value)) continue;
			pattern.lastIndex = 0;
			const out = document.createDocumentFragment();
			let at = 0;
			for (const hit of value.matchAll(pattern)) {
				out.append(value.slice(at, hit.index));
				const mark = document.createElement('mark');
				mark.className = 'review-changed';
				mark.textContent = hit[0];
				out.append(mark);
				at = (hit.index ?? 0) + hit[0].length;
			}
			out.append(value.slice(at));
			t.replaceWith(out);
		}
	}

	let open = $state<'edit' | 'discard' | null>(null);
	let busy = $state(false);
	let said = $state('');
	let text = $state('');
	let name = $state('');
	let field = $state<HTMLTextAreaElement | null>(null);

	function panel(which: 'edit' | 'discard'): void {
		said = '';
		if (open === which) {
			open = null;
			return;
		}
		text = which === 'edit' ? (record.statement ?? '') : '';
		name = record.local ?? '';
		open = which;
		void Promise.resolve().then(() => field?.focus());
	}

	async function send(endpoint: string, body: Record<string, unknown>): Promise<void> {
		if (busy) return;
		busy = true;
		said = '';
		const res = await write(endpoint, { node: id, ...body });
		busy = false;
		if (res.ok) {
			open = null;
			onacted();
			void store.refresh();
		} else said = res.error?.message ?? 'the publisher refused it';
	}

	export function verify(): void {
		void send('library-verify', {});
	}
	export function edit(): void {
		panel('edit');
	}
	export function discard(): void {
		panel('discard');
	}
	/** Edit-then-verify: the rendering, the name, or both; only what the author changed is sent. */
	function verifyEdited(): void {
		const body: Record<string, unknown> = {};
		if (text.trim() && text.trim() !== (record.statement ?? '').trim()) body.statement = text.trim();
		if (name.trim() && name.trim() !== (record.local ?? '')) body.local = name.trim();
		void send('library-verify', body);
	}
	const discarding = () => text.trim() && send('library-discard', { why: text.trim() });
	// a new proposal shown in the card starts with nothing open
	$effect(() => {
		void id;
		untrack(() => {
			open = null;
			said = '';
		});
	});
</script>

<article class="card" data-testid="proposal" data-id={id} bind:clientWidth={width}>
	<header>
		<h3 data-testid="proposal-name">{named} · {surnames(ref?.bib.author)}, <em><Tex text={bibText(ref?.bib.title) || citekey} /></em>{#if record.page}, p. {record.page}{/if}</h3>
		<details class="facts">
			<summary>details</summary>
			<p><code>{id}</code> · {#if record.page}the PDF <code>{record.artifact}</code>{:else}<code>{record.source_file ?? 'the source'}</code>{/if} · level {record.level} · read by {proposer}</p>
		</details>
	</header>

	<section class="paper-words" data-testid="proposal-source">
		<h4>{record.page ? 'the page says' : 'the source says'}</h4>
		{#if paper && record.page && rects.length}
			<div class="crop" style:height="{crop}px" data-testid="proposal-paper">
				<PdfDoc url={paper} page={record.page} scale={scale} window={0} spans={[{ id, page: record.page, rects }]} focus={id} />
			</div>
		{:else if record.page_text}
			<p class="verbatim" data-testid="proposal-page">{#each marked(record.page_text, record.source_text ?? '') as part, i (i)}{#if part.hit}<mark>{part.text}</mark>{:else}{part.text}{/if}{/each}</p>
		{:else}
			<p class="verbatim">{record.source_text}</p>
		{/if}
		{#if !paper && record.page}<p class="muted" data-testid="proposal-noimage">no copy of the paper on this machine, so symbols can be judged only from the text above</p>{/if}
	</section>

	<section class="rendering" data-testid="proposal-statement">
		<h4>rendered as</h4>
		{#if node?.fragment}
			{#key id}<Fragment path={node.fragment} macroSet={citekey} authoring={false} anchor="" standalone onmounted={markWords} />{/key}
		{:else}
			<p class="rendered"><Statement text={record.statement ?? ''} /></p>
		{/if}
		{#if record.not_on_page?.length}
			<p class="added" data-testid="proposal-added">{record.not_on_page.length} word{record.not_on_page.length === 1 ? '' : 's'} not found on the page</p>
		{/if}
	</section>

	{#if open}
		<div class="pop" data-testid="proposal-panel">
			<label for="pc-{id}">{open === 'edit' ? 'your rendering — the page text and the anchor are untouched' : 'why this should not stand, in one line: the next agent that proposes it is told'}</label>
			<textarea id="pc-{id}" rows={open === 'edit' ? 4 : 2} bind:value={text} bind:this={field} data-testid="proposal-text" onkeydown={(e) => e.key === 'Escape' && (open = null)}></textarea>
			{#if open === 'edit'}
				<label for="pn-{id}">the paper's name for it</label>
				<input id="pn-{id}" class="name" bind:value={name} data-testid="proposal-name-field" />
			{/if}
			<div class="row">
				<button type="button" class="ghost" onclick={() => (open = null)}>Cancel</button>
				{#if open === 'edit'}
					<button type="button" class="primary" disabled={busy || !text.trim()} onclick={verifyEdited} data-testid="proposal-send">Verify as edited</button>
				{:else}
					<button type="button" class="primary danger" disabled={busy || !text.trim()} onclick={discarding} data-testid="proposal-send">Discard</button>
				{/if}
			</div>
		</div>
	{/if}
	{#if said}<p class="said" role="status" data-testid="proposal-said">{said}</p>{/if}

	{#if writable}
		<footer class="verbs">
			<button type="button" class="verb" onclick={verify} disabled={busy} data-testid="proposal-verify">verify <kbd>v</kbd></button>
			<button type="button" class="verb" onclick={edit} aria-expanded={open === 'edit'} data-testid="proposal-edit">edit <kbd>e</kbd></button>
			<button type="button" class="verb danger" onclick={discard} aria-expanded={open === 'discard'} data-testid="proposal-discard">discard <kbd>d</kbd></button>
		</footer>
	{:else}
		<footer class="verbs"><span class="muted">read-only: this corpus is published, not served</span></footer>
	{/if}
</article>

<style>
	.card {
		border: 1px solid var(--rule-strong);
		border-left: 3px solid var(--state-proposed, var(--link));
		border-radius: var(--rad-control);
		padding: var(--gap) var(--gap);
		background: var(--sheet);
		min-width: 0;
	}
	h3 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
	}
	h4 {
		margin: var(--gap) 0 var(--gap-hair);
		font-family: var(--sans);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--ink-faint);
	}
	.facts summary {
		font-size: 11px;
		color: var(--ink-faint);
		cursor: pointer;
	}
	.facts p {
		margin: 2px 0 0;
		font-size: 11px;
		color: var(--ink-soft);
		overflow-wrap: anywhere;
	}
	/* the page the card's width, trimmed to the statement and scrolled to it; a statement taller than the window scrolls inside it */
	.crop {
		overflow: hidden;
		border: 1px solid var(--rule);
		border-radius: 4px;
		max-height: 60vh;
	}
	.crop :global(.doc),
	.crop :global(.column) {
		height: 100%;
	}
	.crop :global(.column) {
		padding: 0;
	}
	.verbatim {
		white-space: pre-wrap;
		font-size: 0.92em;
		margin: 0;
		overflow-wrap: anywhere;
	}
	.rendering :global(.fragment),
	.rendered {
		overflow-wrap: anywhere;
	}
	.rendering :global(mark.review-changed) {
		color: inherit;
		background: var(--review-add, var(--mark));
	}
	.added {
		margin: var(--gap-hair) 0 0;
		font-size: 11.5px;
		color: var(--state-stale);
	}
	.pop {
		display: grid;
		gap: 4px;
		margin-top: var(--gap);
	}
	.pop textarea,
	.pop .name {
		font: inherit;
		width: 100%;
		box-sizing: border-box;
	}
	.pop label {
		font-size: 11px;
		color: var(--ink-soft);
	}
	.row {
		display: flex;
		gap: 8px;
		justify-content: flex-end;
	}
	.said {
		color: var(--state-incomplete);
		font-size: 12px;
	}
	.verbs {
		display: flex;
		gap: 12px;
		margin-top: var(--gap);
		padding-top: var(--gap-tight);
		border-top: 1px solid var(--rule);
	}
	.verb {
		font: inherit;
		font-size: 12.5px;
		color: var(--link);
		background: none;
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 3px 10px;
		cursor: pointer;
	}
	.verb.danger {
		color: var(--state-incomplete);
	}
	.verb kbd {
		font: inherit;
		font-size: 10px;
		color: var(--ink-faint);
		margin-left: 4px;
	}
	.primary {
		font: inherit;
		color: var(--paper);
		background: var(--link);
		border: 0;
		border-radius: var(--rad-control);
		padding: 3px 12px;
		cursor: pointer;
	}
	.primary.danger {
		background: var(--state-incomplete);
	}
	.ghost {
		font: inherit;
		background: none;
		border: 0;
		color: var(--ink-soft);
		cursor: pointer;
	}
</style>
