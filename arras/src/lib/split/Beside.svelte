<script lang="ts">
	// The split as a **mode of a route** (plan 0.13 §7, DR-202), rather than a route of its own.
	//
	// A page wraps whatever it already renders in this, and gains a discussion beside it when the reader asks for one.
	// The mode is in the URL — `?beside` — so an opened split is a link, back closes it, and a reader who has never
	// wanted one carries no extra chrome but a single control.
	//
	// The content pane keeps the page's own scroll; the frame is what gets the height, because a split whose two sides
	// scroll together is one pane with a line drawn down it.
	import type { Snippet } from 'svelte';
	import { page } from '$app/state';
	import { rail } from '$lib/shell/rail.svelte';
	import Split from './Split.svelte';
	import Discussion from './Discussion.svelte';
	import BesideToggle from './BesideToggle.svelte';

	let {
		children,
		keys = [],
		label = 'content',
		session = '',
		open = false,
		control = true,
		head
	}: {
		children: Snippet;
		keys?: readonly string[];
		label?: string;
		/** Which session the discussion is of; empty means the one loom is writing into. */
		session?: string;
		/** Whether this route opens split. A session's permalink does, because the discussion is what it is for. */
		open?: boolean;
		/** Whether to draw the toggle in a band above the content. A view with a rail of its own renders `BesideToggle` there instead and passes `false`; this goes when every reading view has one. */
		control?: boolean;
		head?: Snippet;
	} = $props();

	const on = $derived((page.url.searchParams.get('beside') ?? (open ? '1' : '0')) === '1');

	// The discussion pane stands where the page rail stands, so the rail goes while the split is open and comes back
	// when it closes. Two columns of context either side of a measured column is not a reading layout.
	$effect(() => {
		rail.beside = on;
		return () => {
			rail.beside = false;
		};
	});
</script>

{#if control}
	<p class="beside-control"><BesideToggle {open} /></p>
{/if}

{#if on}
	<div class="frame" data-testid="beside">
		<Split contentLabel={label} discussionLabel="discussion">
			{#snippet content()}
				<div class="held">{@render children()}</div>
			{/snippet}
			{#snippet discussion()}
				<Discussion {keys} {session} {head} />
			{/snippet}
		</Split>
	</div>
{:else}
	{@render children()}
{/if}

<style>
	.beside-control {
		margin: 0 0 var(--gap-tight);
		font-family: var(--sans);
		font-size: 10px;
		text-align: right;
	}
	/* **The split is the page, not a card on it.** It was 80vh inside a padded column, so a fifth of every screen was
	   empty below it and a rule was drawn round the whole thing. It now fills what the shell leaves it, edge to edge,
	   with no border of its own -- the divider is the only line the reader needs. */
	.frame {
		height: 100%;
		min-height: 0;
	}
	.held {
		padding: var(--gap) var(--gap-wide) var(--gap) var(--gap);
	}
</style>
