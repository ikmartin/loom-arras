<script lang="ts">
	// What stands in the discussion pane (plan 0.13 §7): the session being written to, the annotations on what the
	// content pane is showing, the messages as they land, and the composer docked in the foot.
	//
	// One component for every route that opens the split, because the discussion is the same discussion wherever the
	// content came from. What differs between an authoring node, a document and a cited work is the keys it is about,
	// and that is a prop.
	import type { Annotation } from '$lib/manifest/types';
	import { store } from '$lib/manifest/client.svelte';
	import { onAny } from '$lib/annotations';
	import { active, hidden, sessionView } from '$lib/sessions/sessions.svelte';
	import { travel } from '$lib/travel/travel';
	import Prose from '$lib/math/Prose.svelte';
	import Stream from '$lib/sessions/Stream.svelte';
	import Composer from '$lib/sessions/Composer.svelte';
	import type { Snippet } from 'svelte';

	let { keys = [], session = '', head }: { keys?: readonly string[]; session?: string; head?: Snippet } = $props();

	const m = $derived(store.manifest);
	const here = $derived(active(m));
	const shown = $derived<Annotation[]>(m ? onAny(m, keys).filter((a) => !a.discarded) : []);
	// What the selection is keeping off the page. Said rather than left to be inferred: a page can look lightly
	// annotated when it is not, and a reader who does not know that trusts the wrong picture.
	const kept = $derived(m ? hidden(m, keys.flatMap((k) => Object.values(m.annotations ?? {}).filter((a) => a.target.key === k && !a.in_reply_to && !a.discarded))) : 0);

	/** From the pane back to the mark in the content, which is the direction this side of the split travels in. */
	function go(id: string, from: Element): void {
		travel(document.querySelector(`[data-annotation~=${JSON.stringify(id)}]`), from);
	}
</script>

<div class="stack" data-testid="discussion">
	<div class="body">
		{#if here}
			<p class="into" data-testid="discussion-into">writing to <strong>{here.title}</strong></p>
		{/if}
		{#if head}{@render head()}{/if}
		{#if keys.length}
			<ul class="plain notes">
				{#each shown as a (a.id)}
					<li data-testid="beside-{a.id}">
						<button type="button" class="as-link" onclick={(e) => go(a.id, e.currentTarget)}>{a.kind}</button>
						{#if a.target.page}<span class="page" data-testid="beside-page-{a.id}">p.{a.target.page}{a.basis === 'box' ? ' (box)' : ''}</span>{/if}
						<span class="who">{a.author.label ?? a.author.id}</span>
						{#if a.quote}<span class="quote">“{a.quote}”</span>{/if}
						<Prose html={a.body_html} />
					</li>
				{:else}
					<li class="muted">Nothing is on this yet.</li>
				{/each}
			</ul>
			{#if kept}
				<p class="muted" data-testid="beside-hidden">
					{kept} hidden by the session being shown.
					<button type="button" class="as-link" onclick={() => ((sessionView.showing = 'all'), sessionView.save())}>Show all</button>
				</p>
			{/if}
		{/if}
		<Stream {session} />
	</div>
	<!-- docked in the discussion pane's foot, which is where a reply to what is beside it belongs -->
	<Composer {session} />
</div>

<style>
	.stack {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		position: relative;
	}
	.body {
		flex: 1 1 auto;
		overflow: auto;
		padding: 8px 12px;
		font-family: var(--sans);
		font-size: 11px;
	}
	.into {
		margin: 0 0 var(--gap-tight);
		color: var(--ink-soft);
	}
	.notes {
		margin: 0;
	}
	.notes li + li {
		margin-top: var(--gap-tight);
	}
	.who,
	.page {
		color: var(--ink-faint);
	}
	.quote {
		display: block;
		color: var(--ink-faint);
	}
</style>
