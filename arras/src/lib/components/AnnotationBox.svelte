<script lang="ts">
	// An annotation's box: a title line of its type's name, none for an untyped annotation, with the × when the box can be closed; the body; one line linking to the open suggested edit that answers it, when one does; then one meta line of author, date and the verbs. The stripe and the title take the annotation's own colour, and an anchored annotation's quote is its mark. A settled (resolved) box has its stripe at half strength, its body softened, and the outcome once on the meta line.
	import TexProse from '$lib/math/TexProse.svelte';
	import VerbRow from '$lib/review/VerbRow.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import type { Annotation } from '$lib/manifest/types';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import { settled } from '$lib/fragments/mount';
	import { lookVars, typeOf } from '$lib/review/annotationTypes';
	import { editAnswering } from '$lib/review/suggestions';
	import { route } from '$lib/paths';
	import { travel } from '$lib/travel/travel';

	let { annotation, replies = [], onclose }: { annotation: Annotation; replies?: Annotation[]; onclose?: () => void } = $props();

	const done = $derived(settled(annotation));
	/** The quote is shown only where no mark stands for the annotation -- unanchored, or detached -- since there it is the only record of the words. */
	const quoted = $derived(!!annotation.quote && (!annotation.anchored || annotation.detached));
	/** What settled it, said once on the meta line; '' while open. */
	const outcome = $derived(annotation.status === 'open' ? '' : annotation.status);
	/** The open suggested edit that answers it, decided in Review's Proposed Changes. */
	const edit = $derived(editAnswering(store.manifest, annotation.id));

	/** The type's name as the quilt now has it; '' for an untyped annotation or one whose type was deleted. */
	const title = $derived(typeOf(store.manifest, annotation)?.name ?? '');

	/** Double-click travels to this annotation's mark, the one in the box's own pane first (plan 0.13 §7). A detached annotation, or one anchored in another document, has no mark here, and nothing is invented for it. */
	function go(e: MouseEvent): void {
		e.preventDefault();
		const from = e.currentTarget as Element;
		const sel = `[data-annotation~="${CSS.escape(annotation.id)}"]`;
		travel(from.closest('[data-pane]')?.querySelector(sel) ?? document.querySelector(sel), from);
	}
</script>

<article class="box" class:settled={done} style={lookVars(annotation.look)} id="ann-{annotation.id}" data-annotation-id={annotation.id} ondblclick={go}>
	{#if title || onclose}
		<div class="title">
			<span class="kind" data-testid="box-type">{title}</span>
			<!-- the host's one ×, on the first box's title line; a box that stands open beside a comparison has none -->
			{#if onclose}<button type="button" class="comment-close" title="Close" aria-label="Close this annotation" onclick={(e) => { e.stopPropagation(); onclose(); }}>×</button>{/if}
		</div>
	{/if}
	<!-- the quote is the source's TeX: typeset, so `$c$` reads as the formula it is -->
	{#if quoted}<blockquote class="quote"><TexProse text={annotation.quote ?? ''} /></blockquote>{/if}
	<div class="body"><Prose html={annotation.body_html} /></div>
	{#if edit}<p class="answered" data-testid="box-edit">A suggested edit answers it: <a href="{route('/review/proposed')}#{edit.id}">see it in Proposed Changes</a>.</p>{/if}
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
						<!-- A reply is an annotation with `in_reply_to` set, so deleting one is `delete` on its own id. -->
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
		/* the stripe is the annotation's colour, from the look's variables on the box (theme.css, beside the mark's) */
		border-left: 3px solid var(--ann-line);
		border-radius: var(--rad-control);
		padding: var(--gap-tight) calc(var(--gap-tight) + 2px);
		margin: var(--gap-tight) 0;
		/* the reader chose a body size; a finding about the text is read alongside it, one notch down */
		font-size: calc(var(--body-size) * 0.92);
		line-height: 1.5;
		overflow-wrap: anywhere;
	}
	/* The title: the type's name in the annotation's colour, and the × at the right of the same line. */
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
		color: var(--ann-line);
	}
	.settled .kind {
		color: color-mix(in srgb, var(--ann-line) 50%, transparent);
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
	/* The suggested edit that answers it: one quiet line, its link the way to decide it. */
	.answered {
		margin: var(--gap-hair) 0 0;
		font-family: var(--sans);
		font-size: 0.8em;
		color: var(--ink-soft);
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
