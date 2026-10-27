<script lang="ts">
	// An annotation's box: a title line of the kind in its hue, and the severity after an objection's or a suggestion's, with the × when the box can be closed; the body; then what its kind adds -- a suggestion's proposed text at a rule in the suggestion's hue, a citation's work at one in the citation's -- then one meta line of author, date and the verbs. The kind is both the title and the stripe's hue; an open box is open, severity is the mark's weight, and an anchored annotation's quote is its mark. A settled box (resolved or withdrawn) has its stripe at half strength, its body softened, and the outcome once on the meta line.
	import TexProse from '$lib/math/TexProse.svelte';
	import TexHtml from '$lib/math/TexHtml.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import VerbRow from '$lib/review/VerbRow.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import type { Annotation } from '$lib/manifest/types';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import { settled } from '$lib/fragments/mount';
	import { decided } from '$lib/review/decisions.svelte';
	import { travel } from '$lib/travel/travel';

	let { annotation, replies = [], onclose }: { annotation: Annotation; replies?: Annotation[]; onclose?: () => void } = $props();

	const done = $derived(settled(annotation));
	/** The quote is shown only where no mark stands for the annotation -- unanchored, or detached -- since there it is the only record of the words. */
	const quoted = $derived(!!annotation.quote && (!annotation.anchored || annotation.detached));
	/** One word for where the proposed text would go; `proposed` when the suggestion carries no placement. */
	const word = $derived(annotation.placement === 'replace' || annotation.placement === 'after' || annotation.placement === 'before' ? annotation.placement : 'proposed');

	/** What settled it, said once on the meta line: a citation's `accepted` (a reference note names it) or `rejected` (decided from this box), else `resolved` or `withdrawn`; '' while open. */
	function outcomeOf(a: Annotation): string {
		if (a.discarded || a.status === 'discarded') return 'withdrawn';
		if (a.kind === 'citation') {
			if (store.manifest?.reference_notes?.some((n) => n.from?.annotation === a.id)) return 'accepted';
			if (decided[a.id]) return decided[a.id];
		}
		if (a.applied) return 'applied';
		return a.status === 'open' ? '' : a.status;
	}
	const outcome = $derived(outcomeOf(annotation));

	const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
	/** `Objection (Major)`: the kind, and the severity where the kind takes one and the annotation has one. */
	const title = $derived(
		cap(annotation.kind) + ((annotation.kind === 'objection' || annotation.kind === 'suggestion') && annotation.severity ? ` (${cap(annotation.severity)})` : '')
	);

	/** Double-click travels to this annotation's mark, the one in the box's own pane first (plan 0.13 §7). A detached annotation, or one anchored in another document, has no mark here, and nothing is invented for it. */
	function go(e: MouseEvent): void {
		e.preventDefault();
		const from = e.currentTarget as Element;
		const sel = `[data-annotation~="${CSS.escape(annotation.id)}"]`;
		travel(from.closest('[data-pane]')?.querySelector(sel) ?? document.querySelector(sel), from);
	}

	/** How the proposed text is shown: rendered (what opens), as written, the key with it in place, or the patch that takes it. */
	let view = $state<'rendered' | 'verbatim' | 'place' | 'patch'>('rendered');
	const change = $derived(annotation.status === 'open' ? annotation.change : undefined);
	const ready = $derived(change?.state === 'ready' ? change : undefined);
	/** The key as it would read with the suggestion taken, fetched when first asked for. */
	let inPlace = $state('');
	$effect(() => {
		const path = view === 'place' ? ready?.fragment : undefined;
		if (!path) return;
		let dropped = false;
		void fetchFragment(path, store.hash)
			.then((html) => !dropped && (inPlace = html))
			.catch(() => !dropped && (inPlace = ''));
		return () => {
			dropped = true;
		};
	});
	const pick = (v: typeof view) => (view = view === v ? 'rendered' : v);
</script>

<article class="box k-{annotation.kind}" class:settled={done} id="ann-{annotation.id}" data-annotation-id={annotation.id} ondblclick={go}>
	<div class="title">
		<span class="kind" data-testid="box-kind">{title}</span>
		<!-- the host's one ×, on the first box's title line; a box that stands open beside a comparison has none -->
		{#if onclose}<button type="button" class="comment-close" title="Close" aria-label="Close this annotation" onclick={(e) => { e.stopPropagation(); onclose(); }}>×</button>{/if}
	</div>
	<!-- the quote is the source's TeX: typeset, so `$c$` reads as the formula it is -->
	{#if quoted}<blockquote class="quote"><TexProse text={annotation.quote ?? ''} /></blockquote>{/if}
	<div class="body"><Prose html={annotation.body_html} /></div>
	{#if annotation.kind === 'citation'}
		{#if annotation.payload}
			<!-- the work proposed, as prose; the body above is the claim it would support -->
			<div class="cite" data-testid="work"><TexProse text={annotation.payload} /></div>
		{/if}
	{:else if annotation.payload != null}
		<!-- Text the annotation proposes, where its `placement` says it goes: the payload itself, as written, the key with it in place, or the patch that takes it. Loom applies nothing; the author does. -->
		<div class="pay" data-testid="payload" data-placement={word}>
			<!-- the switches stand with the word, so they keep their place whichever way the text is shown -->
			<p class="head">
				<span class="word">{word}</span>
				<button type="button" class="as-link switch" aria-pressed={view === 'verbatim'} data-testid="payload-view" onclick={() => (view = view === 'rendered' ? 'verbatim' : 'rendered')}>· {view === 'rendered' ? 'verbatim' : 'rendered'}</button>
				{#if ready}
					<button type="button" class="as-link switch" aria-pressed={view === 'place'} data-testid="payload-in-place" onclick={() => pick('place')}>· in place</button>
					<button type="button" class="as-link switch" aria-pressed={view === 'patch'} data-testid="payload-patch" onclick={() => pick('patch')}>· patch</button>
				{/if}
			</p>
			{#if change?.state === 'taken'}
				<p class="said" data-testid="payload-taken">The text now reads as this suggestion taken.</p>
			{:else if change?.state === 'unplaced'}
				<p class="said" data-testid="payload-unplaced">Not shown in place: {change.why}.</p>
			{/if}
			{#if view === 'place' && ready}
				<!-- the key as it would read, its changed words marked as Review marks them -->
				{#if ready.moved}<p class="said" data-testid="payload-moved">The text has changed since this was written; the words it quotes still stand.</p>{/if}
				<div class="in-place" data-testid="payload-in-place-view"><TexHtml html={inPlace} /></div>
			{:else if view === 'patch' && ready}
				<div data-testid="payload-patch-view"><DiffView path={ready.diff} /></div>
			{:else if view === 'verbatim'}
				<!-- the source as written: one block, its line breaks and indentation kept, since it is what would be pasted -->
				<pre data-testid="payload-verbatim">{annotation.payload}</pre>
			{:else}
				<!-- rendered by the publisher where it could be, since a proposal may be a whole theorem and its proof; a deletion has nothing to render -->
				<div data-testid="payload-rendered">{#if annotation.payload === ''}<span class="said">the quoted words, deleted</span>{:else if annotation.payload_html}<TexHtml html={annotation.payload_html} />{:else}<TexProse text={annotation.payload} />{/if}</div>
			{/if}
		</div>
	{/if}
	<div class="meta">
		<span class="who"><span class="author" title={annotation.author.id}>{annotation.author.label ?? annotation.author.id}</span> · {shortDate(annotation.created)}{#if outcome}<span class="outcome" data-testid="outcome"> · {outcome}</span>{/if}</span>
		<VerbRow {annotation} />
	</div>
	{#if replies.length}
		<div class="replies">
			{#each replies as r (r.id)}
				<article class="reply" id="ann-{r.id}" data-annotation-id={r.id}>
					<div class="body"><Prose html={r.body_html} /></div>
					<div class="meta">
						<span class="who"><span class="author" title={r.author.id}>{r.author.label ?? r.author.id}</span> · {shortDate(r.created)}</span>
						<!-- A reply is an annotation with `in_reply_to` set, so withdrawing one is `discard` on its own id; nothing is deleted from the log. -->
						<VerbRow annotation={r} compact />
					</div>
				</article>
			{/each}
		</div>
	{/if}
</article>

<style>
	.box {
		background: var(--sheet);
		border: 1px solid var(--rule);
		/* the stripe is the kind: its hue comes from `k-<kind>` (theme.css, beside the mark's), the neutral for a note or a kind the viewer has never heard of */
		border-left: 3px solid var(--ann-hue);
		border-radius: var(--rad-control);
		padding: var(--gap-tight) calc(var(--gap-tight) + 2px);
		margin: var(--gap-tight) 0;
		/* the reader chose a body size; a finding about the text is read alongside it, one notch down */
		font-size: calc(var(--body-size) * 0.92);
		line-height: 1.5;
		overflow-wrap: anywhere;
	}
	/* The title: the kind in its hue, with its severity where it has one, and the × at the right of the same line. */
	.title {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--gap-tight);
		margin-bottom: var(--gap-hair);
		font-family: var(--sans);
		font-size: calc(var(--body-size) * 0.8);
		line-height: 1.3;
	}
	.kind {
		font-weight: 600;
		letter-spacing: 0.01em;
		color: var(--ann-hue);
	}
	.settled .kind {
		color: color-mix(in srgb, var(--ann-hue) 50%, transparent);
	}
	.body {
		font-family: var(--body-face);
	}
	.body :global(p) {
		margin: 0.25em 0;
	}
	.body :global(p:first-child) {
		margin-top: 0;
	}
	.settled .body {
		color: var(--ink-soft);
	}
	.quote {
		margin: 0 0 var(--gap-hair);
		padding-left: var(--gap-tight);
		border-left: 2px solid var(--mark);
		color: var(--ink-soft);
		font-family: var(--body-face);
		font-style: italic;
	}
	/* What the kind adds, each at a 2px rule in its own hue. */
	.pay,
	.cite {
		margin: var(--gap-hair) 0 var(--gap-tight);
		padding: 2px 0 2px 10px;
		font-family: var(--body-face);
	}
	.pay {
		border-left: 2px solid var(--ann-suggestion);
	}
	.cite {
		border-left: 2px solid var(--ann-citation);
	}
	.pay .head {
		margin: 0 0 2px;
		line-height: 1.3;
	}
	.pay .word {
		font-family: var(--sans);
		font-size: 0.78em;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--ann-suggestion);
	}
	.pay pre {
		margin: 0;
		padding: 6px 8px;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		font-size: 0.8em;
		line-height: 1.45;
	}
	.switch {
		font-family: var(--sans);
		font-size: 0.8em;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
	}
	.switch:hover,
	.switch[aria-pressed='true'] {
		color: var(--ink-soft);
	}
	.said {
		margin: 2px 0;
		font-family: var(--sans);
		font-size: 0.8em;
		color: var(--ink-soft);
	}
	/* the key with the suggestion taken: what it adds washed in the accepted state's hue, as Review washes a change */
	.in-place :global(mark.review-changed) {
		color: inherit;
		background: color-mix(in srgb, var(--state-accepted) 18%, transparent);
	}
	.in-place :global(.math.review-changed) {
		background-color: color-mix(in srgb, var(--state-accepted) 18%, transparent);
	}
	/* One line: who and when at the left, the verbs at the right, the verbs dropping to their own line when the box is narrow; a reply, a restatement or a reason being written takes the full width beneath them. */
	.meta {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: baseline;
		gap: 2px 14px;
		margin-top: var(--gap-hair);
		font-family: var(--sans);
		font-size: calc(var(--body-size) * 0.76);
		letter-spacing: 0.02em;
		color: var(--ink-faint);
	}
	.who {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 100%;
	}
	.replies {
		margin-top: var(--gap-tight);
		padding-left: 0.8rem;
		border-left: 1px solid var(--rule);
	}
	.reply + .reply {
		margin-top: var(--gap-tight);
	}
</style>
