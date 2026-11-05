<script lang="ts">
	// The notes on the item a pane shows (plan 0.22.8), quiet at its head and to its right, costing the item no height: folded to a count until opened, each with the words it quotes, who wrote it and when, a link to its place, and Keep, which stops it fading. A faded note is hidden until the reader shows them. A session's notes are read in its transcript instead, where they entered the discussion.
	import { store } from '$lib/manifest/client.svelte';
	import type { Manifest, Note } from '$lib/manifest/types';
	import { keep, notesWhere, noteWhere } from '$lib/notes';
	import { can } from '$lib/write';
	import type { Item } from '../item';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest);
	let faded = $state(false);
	let keeps = $state(false);
	$effect(() => {
		void can('note-keep').then((yes) => (keeps = yes));
	});

	/** Whether `n` is on what `item` shows: its file, its work, its node or a node it holds, a key its document reaches, or the research state's file. */
	function on(mm: Manifest, it: Item, n: Note): boolean {
		const t = n.target;
		if (it.kind === 'file') return t.file === it.id;
		if (it.kind === 'work') return t.citekey === it.id;
		if (it.kind === 'page') return !!t.file && t.file === mm.research_state?.path;
		if (!t.key) return false;
		const base = t.key.split('#')[0].split('/proof')[0];
		if (it.kind === 'node' || it.kind === 'context') return base === it.id;
		if (it.kind === 'document') return t.key === it.id || !!mm.nodes[base]?.reached_by?.includes(it.id);
		return false;
	}

	const here = $derived(m && item.kind !== 'session' ? notesWhere(m, (n) => on(m, item, n), true) : []);
	const shown = $derived(here.filter((n) => faded || !n.faded));
	const hidden = $derived(here.length - here.filter((n) => !n.faded).length);
</script>

{#if here.length}
	<details class="notes-here" data-testid="notes-here">
		<summary>{shown.length} {shown.length === 1 ? 'note' : 'notes'}{#if hidden && !faded}<span class="faint"> · {hidden} faded</span>{/if}</summary>
		<ul class="plain">
			{#each shown as n (n.id)}
				<li class="note" class:faded={n.faded} data-testid="note-{n.id}">
					{#if n.mark}<span class="faint">{n.mark} </span>{/if}{#if n.quote}<q class="quoted">{n.quote}</q>{/if}
					{#if n.body}<span class="body">{n.body}</span>{/if}
					<span class="faint">
						· <a href="quilt:{n.id}">{noteWhere(n)}</a> · {n.author.id} · {n.when.slice(0, 10)}{#if n.detached} · {n.quote ? 'its words are gone' : 'the file has changed'}{/if}{#if n.kept} · kept{/if}
					</span>
					{#if keeps && !n.kept && !n.mark}<button type="button" class="as-link" data-testid="note-keep" onclick={() => keep(n.id)}>keep</button>{/if}
				</li>
			{/each}
		</ul>
		{#if hidden}<button type="button" class="as-link" data-testid="notes-faded" onclick={() => (faded = !faded)}>{faded ? 'hide' : 'show'} {hidden} faded</button>{/if}
	</details>
{/if}

<style>
	.notes-here {
		float: right;
		position: relative;
		z-index: 1;
		max-width: min(24rem, 45%);
		margin: var(--gap-tight) 24px 0 var(--gap);
		font-size: 0.9em;
		color: var(--ink-soft);
		background: var(--paper, transparent);
	}
	.notes-here summary {
		cursor: pointer;
		color: var(--ann-neutral);
	}
	.note {
		margin: var(--gap-hair) 0;
	}
	.note.faded {
		opacity: 0.6;
	}
	.quoted {
		font-style: italic;
	}
</style>
