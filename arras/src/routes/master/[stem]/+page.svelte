<script lang="ts">
	// The read view (book 15.3.1): the document rendered as a document in a measured column, with the margin annotation in the left gutter and the comments in the right.
	// The gutters use the site generator's algebra, so a corpus page and a note page are laid out alike; the environment's taxon accent stands on the boundary between the left gutter and the text.
	import { mount, unmount, untrack, type Component } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import type { CommentSlot } from '$lib/fragments/mount';
	import type { Annotation } from '$lib/manifest/types';
	import { anchorId, keyUrl, masterStem, masterUrl } from '$lib/nav';
	import { prefs } from '$lib/prefs.svelte';
	import { followNodes, reading } from '$lib/reading.svelte';
	import LocalGraphPanel from '$lib/graph/LocalGraphPanel.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	import { dataUrl } from '$lib/paths';
	import { repliesTo } from '$lib/annotations';
	import { commentsOn, slotsFor } from '$lib/fragments/slots';
	import Composer from '$lib/review/Composer.svelte';
	import Beside from '$lib/split/Beside.svelte';

	const m = $derived(store.manifest!);
	const stem = $derived(decodeURIComponent(page.params.stem ?? ''));
	const master = $derived(m.masters.find((x) => masterStem(x.path) === stem));
	const reviewKey = $derived(page.url.searchParams.get('review') ?? '');
	const causeIndex = $derived(Number(page.url.searchParams.get('cause') ?? '-1'));
	const reviewCause = $derived(m.keys[reviewKey]?.acceptance?.causes?.[causeIndex]);
	const comparison = $derived(reviewCause?.comparison);
	const acceptedSide = $derived(reviewCause?.kind === 'own-text-changed');
	const incomingKey = $derived(page.url.searchParams.get('incoming') ?? '');
	const incomingChange = $derived(m.incoming?.changes.find((change) => change.key === incomingKey));
	const hasComparison = $derived(!!comparison || !!incomingChange?.incoming);

	/** What the discussion pane beside the document is about: the document itself, and every key it reaches. */
	const inDocument = $derived(master ? [master.path, ...Object.keys(m.nodes).filter((k) => m.nodes[k].reached_by.includes(master.path))] : []);

	/** Annotations on the document itself, as opposed to on anything inside it. */
	const onDocument = $derived(master ? commentsOn(m, master.path) : []);

	const replies = (id: string) => repliesTo(m, id);
	const slots = slotsFor(() => m);
	/** Every comment inline: beside a comparison there is no gutter to put one in. */
	const inlineSlots = (key: string): CommentSlot[] => commentsOn(m, key).map((a) => ({ id: a.id, where: 'inline' }));

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
	$effect(() => {
		const root = docRoot;
		const citation = incomingKey ? page.url.hash.slice(1) : reviewCause?.kind === 'dependency-changed' ? reviewCause.citation : null;
		const target = citation ? document.getElementById(citation) : null;
		if (!root || !target || !root.contains(target)) return;
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
</script>

<main class="page master">
	{#if !m.masters.length}
		<h1>Read</h1>
		<NoDrafts what="documents to read" />
	{:else if !master}
		<h1>Unknown document</h1>
		<p class="muted">No master in this corpus has the stem <code>{stem}</code>.</p>
	{:else}
		<Beside keys={inDocument} label="the document">
		<div class:with-comparison={hasComparison} class="review-layout">
		<div class="gutters-host">
			<div class="gutters">
				<div class="column">
					{#if onDocument.length}
						<!-- An annotation whose target is the document rather than a key. a publisher may target a document as easily as a key, and `commentsOn` was only ever called with node keys, so no viewer has ever shown one. -->
						<section class="doc-annotations" data-testid="document-annotations">
							<p class="head">About this document</p>
							{#each onDocument as a (a.id)}
								<AnnotationBox annotation={a} replies={replies(a.id)} />
							{/each}
						</section>
					{/if}
					<Composer target={master.path} />
					<header class="doc-head">
						<p class="faint">
							<code>{master.path}</code>{master.numbering_known
								? ''
								: ' · not yet numbered: ids shown without numbers'}
							{#if master.pdf}· <a href={dataUrl(master.pdf)}>PDF</a>{/if}
						</p>
					</header>
						{#key hasComparison}<Fragment
						path={master.fragment}
						master={master.path}
						headingLinks
							margins={!hasComparison}
							comments={hasComparison ? inlineSlots : slots}
						onmounted={fill}
					/>{/key}
				</div>
			</div>
		</div>
		{#if incomingChange?.incoming}
			<aside class="review-comparison" data-testid="incoming-comparison" aria-label="Incoming comparison">
				<header><strong>Incoming · {incomingKey}</strong><a href={`${masterUrl(master.path)}${page.url.hash}`}>close</a></header>
				<Fragment path={incomingChange.incoming} macroSet={incomingChange.incoming_macros} isolatedMacros />
			</aside>
		{:else if comparison}
			<aside class="review-comparison" data-testid="review-comparison" aria-label="Review comparison">
				<header><strong>{acceptedSide ? 'Last accepted' : 'Current'} · {reviewCause?.id ?? reviewKey}</strong><a href={`${masterUrl(master.path)}${page.url.hash}`}>close</a></header>
				<Fragment path={acceptedSide ? comparison.accepted : comparison.current} macroSet={acceptedSide ? comparison.accepted_macros : ''} isolatedMacros={acceptedSide} />
			</aside>
		{/if}
		</div>
		{#if graphOpen && reading.node}
			<div class="local-float">
				<LocalGraphPanel center={reading.node} master={master.path} {hrefFor} height={240} onclose={() => setGraph(false)} />
			</div>
		{:else if !graphOpen}
			<button class="local-toggle" onclick={() => setGraph(true)} aria-label="Show the local graph" title="local graph" data-testid="local-graph-open"><Icon name="graph" size={16} /></button>
		{/if}
		</Beside>
	{/if}
</main>

<style>
	.review-comparison {
		position: sticky;
		top: var(--gap-wide);
		max-height: calc(100vh - 2 * var(--gap-wide));
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
	@media (max-width: 900px) { .review-layout.with-comparison { display: flex; flex-direction: column; padding-right: 0; } .review-layout > .gutters-host, .review-comparison { width: 100%; } .review-comparison { position: static; max-height: none; } }
	.doc-annotations {
		margin-bottom: var(--gap-wide);
	}
	.doc-annotations .head {
		font-family: var(--sans);
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-tight);
	}
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
