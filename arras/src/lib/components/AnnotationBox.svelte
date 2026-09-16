<script lang="ts">
	import type { Annotation } from '$lib/manifest/types';
	import { shortDate } from '$lib/badges';
	import { ui } from '$lib/ui.svelte';

	let { annotation, replies = [] }: { annotation: Annotation; replies?: Annotation[] } = $props();
	const active = $derived(ui.activeAnnotation === annotation.id);
</script>

<article class="box kind-{annotation.kind}" class:active class:discarded={annotation.discarded} id={'ann-' + annotation.id} data-annotation-id={annotation.id}>
	<header>
		<span class="kind">{annotation.kind}</span>
		<span class="author">{annotation.author.label ?? annotation.author.id}</span>
		<span class="date">{shortDate(annotation.created)}</span>
		<span class="status">{annotation.status}</span>
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
		border: 1px solid var(--rule);
		border-left: 3px solid var(--rule);
		border-radius: 4px;
		padding: 0.5rem 0.75rem;
		margin: 0.5rem 0;
		font-size: 0.92rem;
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
		gap: 0.6rem;
		color: var(--ink-soft);
		font-size: 0.8rem;
	}
	header .kind {
		font-weight: 600;
		color: var(--ink);
	}
	.quote {
		margin: 0.3rem 0;
		padding-left: 0.6rem;
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
