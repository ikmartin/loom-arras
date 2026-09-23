<script lang="ts">
	// The read view for a landmark (book 15.3.1, 17.1): the document as it stood when loom recorded it.
	// A landmark is a document, not a corpus of nodes: nothing in it has an identity, so there are no margins, no heading links, no comments and no local graph. Its own references stay inside the page.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import ReadingActs from '$lib/shell/ReadingActs.svelte';

	const m = $derived(store.manifest!);
	const stem = $derived(decodeURIComponent(page.params.stem ?? ''));
	const doc = $derived(m.canon?.find((x) => x.stem === stem));
</script>

<main class="page master">
	{#if !doc}
		<h1>Unknown landmark</h1>
		<p class="muted">No canon document in this corpus has the stem <code>{stem}</code>.</p>
	{:else}
		<!-- A landmark's step is its identity rather than a note about it -- flows-v1 and flows-v2 are the same document
		     at two moments -- so it stays, in the rail, while the path and the commit message go the way the master's did. -->
		<ReadingActs>
			{#snippet lead()}
				{#if doc.step}<span class="faint">landmark @{Number(doc.step)}{doc.name ? ' (' + doc.name + ')' : ''}</span>{/if}
			{/snippet}
		</ReadingActs>
		<div class="gutters-host">
			<div class="gutters">
				<div class="column">
					<Fragment path={doc.fragment} macroSet={doc.macros ?? ''} head={false} standalone />
				</div>
			</div>
		</div>
	{/if}
</main>

<style>
	/* the rail above is the top edge of the view: the document runs flush to it, full width, no gutter above */
	main.master {
		padding-top: 0;
		padding-left: 0;
		padding-right: 0;
	}
</style>
