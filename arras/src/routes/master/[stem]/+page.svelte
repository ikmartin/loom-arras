<script lang="ts">
	// The read view (book 15.3.1): the document rendered as a document in a measured column, with the margin annotation in the left gutter and the comments in the right.
	// The gutters use the site generator's algebra, so a corpus page and a note page are laid out alike; the environment's taxon accent stands on the boundary between the left gutter and the text.
	import { mount, unmount, type Component } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import type { CommentPlacement } from '$lib/fragments/mount';
	import type { Annotation } from '$lib/manifest/types';
	import { masterStem } from '$lib/nav';

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
		return commentsOn(key).map((a) => ({ id: a.id, where: plainLength(a) > GUTTER_LIMIT ? 'inline' : 'gutter' }));
	}

	// The fragment is injected HTML, so the cards are mounted into the slots its wiring created rather than rendered by this template. They are unmounted whenever the fragment is replaced, so a reload leaves nothing behind.
	let mounted: Record<string, unknown>[] = [];

	function fill(root: HTMLElement) {
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
	{#if !master}
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
							{#if master.pdf}· <a href={'/build/' + master.pdf}>PDF</a>{/if}
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
