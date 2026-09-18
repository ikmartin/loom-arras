<script lang="ts">
	import type { Annotation } from '$lib/manifest/types';
	import { shortDate } from '$lib/badges';
	import { ui } from '$lib/ui.svelte';

	// `anchor` gives the box the element id marks point at; a copy opened in the text beside the one in a list must not claim the same id
	let { annotation, replies = [], anchor = true }: { annotation: Annotation; replies?: Annotation[]; anchor?: boolean } = $props();
	const active = $derived(ui.activeAnnotation === annotation.id);
</script>

<article class="box kind-{annotation.kind}" class:active class:discarded={annotation.discarded} id={anchor ? 'ann-' + annotation.id : undefined} data-annotation-id={annotation.id}>
	<header>
		<span class="kind">{annotation.kind}</span>
		<span class="date">{shortDate(annotation.created)}</span>
		<span class="status">{annotation.status}</span>
		<span class="author" title={annotation.author.id}>{annotation.author.label ?? annotation.author.id}</span>
		{#if annotation.detached}<span class="detached">detached</span>{/if}
		{#if annotation.discarded}<span class="detached">discarded</span>{/if}
	</header>
	{#if annotation.quote}<blockquote class="quote">{annotation.quote}</blockquote>{/if}
	<div class="body">{@html annotation.body_html}</div>
	{#if replies.length}
		<div class="replies">
			{#each replies as r (r.id)}
				<article class="reply">
					<header><span class="author">{r.author.label ?? r.author.id}</span> <span class="date">{shortDate(r.created)}</span> <span class="kind">{r.kind}</span></header>
					<div class="body">{@html r.body_html}</div>
				</article>
			{/each}
		</div>
	{/if}
</article>

<style>
	.box {
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-left: 3px solid var(--rule);
		border-radius: var(--rad-control);
		padding: var(--gap-tight);
		margin: var(--gap-tight) 0;
		font-size: 11px;
		line-height: 1.5;
		overflow-wrap: anywhere;
	}
	.severity {
		text-transform: uppercase;
		font-size: 0.68em;
		letter-spacing: 0.04em;
		padding: 0 0.3em;
		border-radius: 2px;
		border: 1px solid currentColor;
	}
	.sev-major {
		color: var(--state-incomplete);
	}
	.sev-moderate {
		color: var(--state-draft);
	}
	.sev-minor {
		color: var(--muted);
	}
	.payload {
		margin: 0.4em 0 0;
		padding: 0.4em 0.5em;
		border-left: 2px solid var(--rule);
		overflow-x: auto;
		white-space: pre-wrap;
		font-size: 0.92em;
	}
	.kind-objection {
		background: var(--state-incomplete-wash);
	}
	.box.active {
		border-color: var(--link);
		box-shadow: 0 0 0 2px color-mix(in srgb, var(--link) 25%, transparent);
	}
	.box.discarded {
		opacity: 0.55;
	}
	.kind-objection {
		border-left-color: var(--state-incomplete);
	}
	.kind-suggestion {
		border-left-color: var(--state-stale);
	}
	.kind-question {
		border-left-color: var(--link);
	}
	.kind-ok {
		border-left-color: var(--state-accepted);
	}
	header {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--gap-hair);
		color: var(--ink-faint);
		font-family: var(--sans);
		font-size: 9px;
		letter-spacing: 0.02em;
		margin-bottom: var(--gap-hair);
	}
	header .kind {
		color: var(--ink);
	}
	header .author {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.quote {
		margin: var(--gap-hair) 0;
		padding-left: var(--gap-tight);
		border-left: 2px solid var(--mark);
		color: var(--ink-soft);
		font-style: italic;
	}
	.replies {
		margin-top: 0.4rem;
		padding-left: 0.8rem;
		border-left: 1px solid var(--rule);
	}
	.body :global(p) {
		margin: 0.25rem 0;
	}
</style>
