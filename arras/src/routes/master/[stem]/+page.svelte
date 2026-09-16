<script lang="ts">
	// The read view (book 15.3.1): the document rendered as a document, each node with its margin column. Navigation, the contents tree and the document picker belong to the shell; this page draws none of them.
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import { masterStem } from '$lib/nav';
	import PageRail from '$lib/shell/PageRail.svelte';

	const m = $derived(store.manifest!);
	const stem = $derived(decodeURIComponent(page.params.stem ?? ''));
	const master = $derived(m.masters.find((x) => masterStem(x.path) === stem));

	// The right rail appears only when a node this document reaches carries a comment that has not been discarded (15.3.1).
	const comments = $derived(
		master
			? Object.values(m.annotations)
					.filter((a) => !a.discarded && !a.in_reply_to)
					.filter((a) => {
						const owner = m.keys[a.target.key]?.node ?? a.target.key;
						return m.nodes[owner]?.reached_by?.includes(master.path);
					})
			: []
	);
	const replies = (id: string) => Object.values(m.annotations).filter((a) => a.in_reply_to === id && !a.discarded);
</script>

<main class="page master">
	{#if !master}
		<h1>Unknown document</h1>
		<p class="muted">No master in this corpus has the stem <code>{stem}</code>.</p>
	{:else}
		<header class="doc-head">
			<h1>{master.title || master.path}</h1>
			<p class="muted">
				<code>{master.path}</code>{master.numbering_known ? '' : ' · not yet compiled: ids shown without numbers'}
				{#if master.pdf}· <a href={'/build/' + master.pdf}>PDF</a>{/if}
			</p>
		</header>
		<Fragment path={master.fragment} master={master.path} headingLinks margins />
	{/if}
</main>

{#if comments.length}
	<PageRail>
		<div data-testid="read-comments">
			<p class="rail-label">Comments</p>
			{#each comments as a (a.id)}
				<AnnotationBox annotation={a} replies={replies(a.id)} />
			{/each}
		</div>
	</PageRail>
{/if}

<style>
	main.master {
		padding-left: 110px;
	}
	.doc-head {
		margin-left: -110px;
		padding-left: 110px;
	}
	.doc-head h1 {
		font-family: var(--body-face);
		font-size: 22px;
		font-weight: 500;
	}
</style>
