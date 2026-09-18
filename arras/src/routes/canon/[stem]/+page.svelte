<script lang="ts">
	// The read view for a landmark (book 15.3.1, 17.1): the document as it stood when loom recorded it.
	// A landmark is a document, not a corpus of nodes: nothing in it has an identity, so there are no margins, no heading links, no comments and no local graph. Its own references stay inside the page.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';

	const m = $derived(store.manifest!);
	const stem = $derived(decodeURIComponent(page.params.stem ?? ''));
	const doc = $derived(m.canon?.find((x) => x.stem === stem));
</script>

<main class="page master">
	{#if !doc}
		<h1>Unknown landmark</h1>
		<p class="muted">No canon document in this corpus has the stem <code>{stem}</code>.</p>
	{:else}
		<div class="gutters-host">
			<div class="gutters">
				<div class="column">
					<header class="doc-head">
						<p class="faint">
							<code>{doc.path}</code>
							{#if doc.step}· landmark @{Number(doc.step)}{doc.name ? ' (' + doc.name + ')' : ''}{/if}
							{#if doc.message}· “{doc.message}”{/if}
						</p>
					</header>
					<Fragment path={doc.fragment} macroSet={doc.macros ?? ''} standalone />
				</div>
			</div>
		</div>
	{/if}
</main>

<style>
	main.master {
		padding-left: 0;
		padding-right: 0;
	}
	.doc-head {
		margin-bottom: var(--gap-wide);
	}
</style>
