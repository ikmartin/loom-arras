<script lang="ts">
	// The read view (book 15.3.1): the document rendered as a document in a measured column, with the margin annotation in the left gutter and the comments in the right.
	// The gutters use the site generator's algebra, so a corpus page and a note page are laid out alike; the environment's taxon accent stands on the boundary between the left gutter and the text.
	import { mount, unmount, untrack, type Component } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import type { CommentPlacement } from '$lib/fragments/mount';
	import type { Annotation } from '$lib/manifest/types';
	import { anchorId, keyUrl, masterStem } from '$lib/nav';
	import { prefs } from '$lib/prefs.svelte';
	import { followNodes, reading } from '$lib/reading.svelte';
	import LocalGraphPanel from '$lib/graph/LocalGraphPanel.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	import { dataUrl } from '$lib/paths';

	const m = $derived(store.manifest!);
	const stem = $derived(decodeURIComponent(page.params.stem ?? ''));
	const master = $derived(m.masters.find((x) => masterStem(x.path) === stem));

	/** How much a comment may say before a gutter is the wrong place for it. Measured on the rendered text of the comment and its replies. */
	const GUTTER_LIMIT = 220;

	const replies = (id: string) => Object.values(m.annotations).filter((a) => a.in_reply_to === id && !a.discarded);

	function plainLength(a: Annotation): number {
		const own = a.body_html.replace(/<[^>]*>/g, '').trim().length + (a.quote?.length ?? 0);
		return own + replies(a.id).reduce((n, r) => n + r.body_html.replace(/<[^>]*>/g, '').trim().length, 0);
	}

	/** The undiscarded top-level comments on exactly this key, in manifest order. A proof has an element of its own, so matching a node's proofs here as well would place the same comment twice. */
	function commentsOn(key: string): Annotation[] {
		return Object.values(m.annotations).filter((a) => !a.discarded && !a.in_reply_to && a.target.key === key);
	}

	function placements(key: string): CommentPlacement[] {
		// shown in place, a comment with a mark is reached from its mark; one without gets a count beside its node's label
		if (prefs.comments === 'inline') return commentsOn(key).filter((a) => !(a.anchored && a.quote)).map((a) => ({ id: a.id, where: 'count' }));
		return commentsOn(key).map((a) => ({ id: a.id, where: plainLength(a) > GUTTER_LIMIT ? 'inline' : 'gutter' }));
	}

	// The fragment is injected HTML, so the cards are mounted into the slots its wiring created rather than rendered by this template. They are unmounted whenever the fragment is replaced, so a reload leaves nothing behind.
	let mounted: Record<string, unknown>[] = [];

	// The local graph follows the result being read (book 15.5.1). Whether it is open is a per-reader convenience kept in this browser, so a reader who put it away is not shown it on every document.
	const GRAPH_KEY = 'arras.localGraph';
	let docRoot = $state<HTMLElement | null>(null);
	let graphOpen = $state(false);
	$effect(() => {
		try {
			graphOpen = localStorage.getItem(GRAPH_KEY) === 'open';
		} catch {
			graphOpen = false;
		}
	});
	function setGraph(open: boolean) {
		graphOpen = open;
		try {
			localStorage.setItem(GRAPH_KEY, open ? 'open' : 'closed');
		} catch {
			// the panel still opens for this visit
		}
	}
	$effect(() => {
		const root = docRoot;
		// untracked: the follower reads the position it writes, and an effect that subscribed to that would restart itself on every result the reader passes
		if (root) return untrack(() => followNodes(root));
	});
	// a result this document holds is a jump within it; anything else opens its page
	const hrefFor = (id: string) => (master && m.nodes[id]?.reached_by.includes(master.path) ? '#' + anchorId(id) : keyUrl(m, id));

	function fill(root: HTMLElement) {
		docRoot = root;
		for (const made of mounted) void unmount(made);
		mounted = [];
		for (const slot of root.querySelectorAll<HTMLElement>('aside[data-comment-slot]')) {
			slot.textContent = '';
			for (const id of (slot.dataset.commentSlot ?? '').split(/\s+/).filter(Boolean)) {
				const annotation = m.annotations[id];
				if (!annotation) continue;
				mounted.push(
					mount(AnnotationBox as unknown as Component<{ annotation: Annotation; replies: Annotation[] }>, {
						target: slot,
						props: { annotation, replies: replies(id) }
					}) as Record<string, unknown>
				);
			}
		}
	}
</script>

<main class="page master">
	{#if !m.masters.length}
		<h1>Read</h1>
		<NoDrafts what="documents to read" />
	{:else if !master}
		<h1>Unknown document</h1>
		<p class="muted">No master in this corpus has the stem <code>{stem}</code>.</p>
	{:else}
		<div class="gutters-host">
			<div class="gutters">
				<div class="column">
					<header class="doc-head">
						<p class="faint">
							<code>{master.path}</code>{master.numbering_known
								? ''
								: ' · not yet compiled: ids shown without numbers'}
							{#if master.pdf}· <a href={dataUrl(master.pdf)}>PDF</a>{/if}
						</p>
					</header>
					<Fragment
						path={master.fragment}
						master={master.path}
						headingLinks
						margins
						comments={placements}
						onmounted={fill}
					/>
				</div>
			</div>
		</div>
		{#if graphOpen && reading.node}
			<div class="local-float">
				<LocalGraphPanel center={reading.node} master={master.path} {hrefFor} height={240} onclose={() => setGraph(false)} />
			</div>
		{:else if !graphOpen}
			<button class="local-toggle" onclick={() => setGraph(true)} aria-label="Show the local graph" title="local graph" data-testid="local-graph-open"><Icon name="graph" size={16} /></button>
		{/if}
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
	.local-float {
		position: fixed;
		right: var(--gap-wide);
		bottom: var(--gap-wide);
		z-index: 30;
		width: 300px;
		padding: var(--gap-tight);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		box-shadow: 0 6px 20px rgb(0 0 0 / 12%);
	}
	.local-toggle {
		position: fixed;
		right: var(--gap-wide);
		bottom: var(--gap-wide);
		z-index: 30;
		width: 34px;
		height: 34px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--ink-soft);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 999px;
		box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
		cursor: pointer;
	}
	.local-toggle:hover {
		color: var(--link);
		border-color: var(--link);
	}
</style>
