<script lang="ts">
	// A document (plan 0.13.3 D1–D4, book 15.3.1): a master or a landmark rendered as a document in a measured column, with each result's id and state in the left gutter behind Show ids. No chrome of its own: its controls are the rail's, drawn once for whichever item is current.
	// The gutters use the site generator's algebra, so a corpus page and a note page are laid out alike; the environment's taxon accent stands on the boundary between the left gutter and the text.
	import { mount, unmount, untrack, type Component } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import FragmentNotes from '$lib/fragments/FragmentNotes.svelte';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import type { CommentSlot } from '$lib/fragments/mount';
	import type { Annotation } from '$lib/manifest/types';
	import { anchorId, keyUrl } from '$lib/nav';
	import { followNodes, followReading, reading, sectionIds } from '$lib/reading.svelte';
	import { contentsOf } from '$lib/contents';
	import LocalGraphPanel from '$lib/graph/LocalGraphPanel.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	import { repliesTo } from '$lib/annotations';
	import { commentsOn, slotsFor } from '$lib/fragments/slots';
	import { isLandmark, itemKey, pathFor, type Item } from '../item';
	import { documentState, getPane } from '../state.svelte';
	import { workspace } from '../store.svelte';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const pane = getPane();
	const landmark = $derived(isLandmark(m, item.id));
	const master = $derived(landmark ? undefined : m.masters.find((x) => x.path === item.id));
	const doc = $derived(landmark ? m.canon?.find((c) => c.path === item.id) : undefined);
	const reviewKey = $derived(item.params?.review ?? '');
	const causeIndex = $derived(Number(item.params?.cause ?? '-1'));
	const reviewCause = $derived(m.keys[reviewKey]?.acceptance?.causes?.[causeIndex]);
	const comparison = $derived(reviewCause?.comparison);
	const acceptedSide = $derived(reviewCause?.kind === 'own-text-changed');
	const incomingKey = $derived(item.params?.incoming ?? '');
	const incomingChange = $derived(m.incoming?.changes.find((change) => change.key === incomingKey));
	const hasComparison = $derived(!!comparison || !!incomingChange?.incoming);
	/** Closing a comparison is the document without it, at the same place. */
	const plain = $derived(pathFor(m, { kind: 'document', id: item.id, ...(item.anchor ? { anchor: item.anchor } : {}) }));

	const replies = (id: string) => repliesTo(m, id);
	const slots = slotsFor(() => m);
	const notes = $derived(documentState(item).notes);
	/** Every comment inline: beside a comparison there is no gutter to put one in. */
	const inlineSlots = (key: string): CommentSlot[] => commentsOn(m, key).map((a) => ({ id: a.id, where: 'inline' }));
	/** Only the current item moves the panel's position bar and the local graph: two documents open at once would otherwise fight over one. */
	const current = $derived(workspace.current ? itemKey(workspace.current) === itemKey(item) : false);
	/** A context on screen already draws a local graph; a second one beside it, of whatever result the reading position has reached, would be one graph twice, and of a different result. */
	const contextShown = $derived([0, 1].some((i) => workspace.active(i)?.kind === 'context'));

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
		if (root && current && master) return untrack(() => followNodes(root, pane.scroller()));
	});
	// from the moment the document is current, not once it is typeset: the first entry is marked before any scrolling, and the ids are looked up in the pane as they arrive
	$effect(() => {
		const scroller = pane.scroller();
		if (!scroller || !current || !master) return;
		const ids = sectionIds(contentsOf(m, master.path));
		return untrack(() => followReading(scroller, ids, scroller));
	});
	$effect(() => {
		const root = docRoot;
		const citation = incomingKey ? (item.anchor ?? '') : reviewCause?.kind === 'dependency-changed' ? reviewCause.citation : null;
		const target = citation && root ? root.querySelector(`[id="${CSS.escape(citation)}"]`) : null;
		if (!target) return;
		target.classList.add('review-citation-target');
		return () => target.classList.remove('review-citation-target');
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

	/** Put a floating panel against the pane rather than inside what scrolls, so it stays put while the document moves under it. */
	function onPane(node: HTMLElement) {
		(pane.frame() ?? node.parentElement)?.appendChild(node);
		return { destroy: () => node.remove() };
	}
</script>

<div class="page item document">
	{#if landmark && doc}
		<div class="gutters-host">
			<div class="gutters">
				<div class="column">
					<Fragment path={doc.fragment} macroSet={doc.macros ?? ''} standalone anchor={item.anchor ?? ''} jump={item.seq} />
				</div>
			</div>
		</div>
	{:else if !m.masters.length}
		<h1>Read</h1>
		<NoDrafts what="documents to read" />
	{:else if !master}
		<h1>Unknown document</h1>
		<p class="muted">No document in this corpus is <code>{item.id}</code>.</p>
	{:else}
		<div class:with-comparison={hasComparison} class="review-layout">
			<div class="gutters-host">
				<div class="gutters">
					<div class="column">
						<FragmentNotes holder={documentState(item)} fallback={master.path}>
							{#key hasComparison}<Fragment
									path={master.fragment}
									master={master.path}
									headingLinks
									annotations={notes}
									margins={!hasComparison}
									comments={hasComparison ? inlineSlots : slots}
									anchor={item.anchor ?? ''}
									jump={item.seq}
									onmounted={fill}
								/>{/key}
						</FragmentNotes>
					</div>
				</div>
			</div>
			{#if incomingChange?.incoming}
				<aside class="review-comparison" data-testid="incoming-comparison" aria-label="Incoming comparison">
					<header><strong>Incoming · {incomingKey}</strong><a href={plain}>close</a></header>
					<Fragment path={incomingChange.incoming} macroSet={incomingChange.incoming_macros} isolatedMacros />
				</aside>
			{:else if comparison}
				<aside class="review-comparison" data-testid="review-comparison" aria-label="Review comparison">
					<header><strong>{acceptedSide ? 'Last accepted' : 'Current'} · {reviewCause?.id ?? reviewKey}</strong><a href={plain}>close</a></header>
					<Fragment path={acceptedSide ? comparison.accepted : comparison.current} macroSet={acceptedSide ? comparison.accepted_macros : ''} isolatedMacros={acceptedSide} />
				</aside>
			{/if}
		</div>
		{#if current && !contextShown}
			{#if graphOpen && reading.node}
				<div class="local-float" use:onPane>
					<LocalGraphPanel center={reading.node} master={master.path} {hrefFor} height={240} onclose={() => setGraph(false)} />
				</div>
			{:else if !graphOpen}
				<button class="local-toggle" use:onPane onclick={() => setGraph(true)} aria-label="Show the local graph" title="local graph" data-testid="local-graph-open"><Icon name="graph" size={16} /></button>
			{/if}
		{/if}
	{/if}
</div>

<style>
	/* the pane's head is the top edge of the view: the document runs flush to it, full width, no gutter above */
	.item.document {
		padding-top: 0;
		padding-left: 0;
		padding-right: 0;
	}
	.review-comparison {
		position: sticky;
		top: var(--gap-wide);
		max-height: calc(100% - 2 * var(--gap-wide));
		min-width: 0;
		overflow-y: auto;
		overflow-x: hidden;
		padding: var(--gap-tight);
		background: var(--sheet);
		border: 1px solid var(--rule);
	}
	.review-layout.with-comparison { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 390px); gap: var(--gap-wide); align-items: start; padding-right: var(--gap-wide); }
	.review-layout > .gutters-host { min-width: 0; }
	.review-comparison header { display: flex; justify-content: space-between; gap: 1rem; margin-bottom: var(--gap-tight); }
	.review-comparison :global(mark.review-changed) { background: var(--state-stale-wash); color: inherit; }
	.review-comparison :global(.math.review-changed) { background-color: var(--state-stale-wash); outline: 2px solid var(--state-stale); }
	.review-comparison :global(.review-change-point) { border-left: 2px solid var(--state-stale); }
	.review-comparison :global(.math.display) { max-width: 100%; overflow-x: auto; overflow-y: hidden; }
	.review-layout :global(.review-citation-target) { background: var(--state-stale-wash); outline: 2px solid var(--state-stale); outline-offset: 2px; scroll-margin-top: var(--gap-wide); }
	/* Against the pane, not the window: in two panes a float at the window's corner would stand over the other one. */
	.local-float {
		position: absolute;
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
		position: absolute;
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
	@container pane (max-width: 900px) { .review-layout.with-comparison { display: flex; flex-direction: column; padding-right: 0; } .review-layout > .gutters-host, .review-comparison { width: 100%; } .review-comparison { position: static; max-height: none; } }
</style>
