<script lang="ts">
	// Reading mode for one work: the page on the left, what is anchored to it on the right (plan 0.13 step 1, item 5).
	//
	// The slice's shape, not the split view — no divider, no placements, no session, nothing written. What it exists to
	// prove is that the three load-bearing pieces meet: loom's anchors draw on a real page, a mark travels to the thing
	// it belongs to, and a selection made in this browser — a third extraction of the page, after the committed text and
	// the word boxes — comes back from loom as an anchor.
	import { artifactUrl, dataUrl } from '$lib/paths';
	import { write, type WriteResult } from '$lib/write';
	import type { Reference } from '$lib/manifest/types';
	import PdfDoc from './PdfDoc.svelte';
	import Split from '$lib/split/Split.svelte';
	import Composer from '$lib/sessions/Composer.svelte';

	let { citekey, ref, page }: { citekey: string; ref: Reference; page: number } = $props();

	/** `build/spans/<scheme>/<id>.json`, as `_attach_spans` writes it. */
	interface Sidecar {
		artifact: string;
		pages: Record<string, { width: number; height: number; rotate: number }>;
		quads: Record<string, number[][]>;
	}

	const url = $derived(ref.artifacts?.pdf ? artifactUrl(ref.artifacts.dir) : '');
	let spans = $state<Sidecar | null>(null);
	let active = $state('');
	let told = $state('');

	// Fetched by the sidecar's own hash rather than derived from the manifest: the manifest is replaced on every poll,
	// and re-fetching geometry once a second is exactly the re-render this pane must not do. Naming the hash is also
	// what lets a stale copy be noticed while the publisher rebuilds underneath.
	$effect(() => {
		const at = ref.spans;
		if (!at) return;
		let dropped = false;
		fetch(dataUrl(at.path))
			.then((r) => (r.ok ? (r.json() as Promise<Sidecar>) : null))
			.then((j) => {
				if (!dropped) spans = j;
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	/** Every anchor's geometry, by the page it is on: the document view draws what belongs to each page it renders. */
	const drawn = $derived(
		Object.entries(spans?.quads ?? {})
			.map(([id, rects]) => ({ id, page: ref.results?.[id]?.page ?? 0, rects }))
			.filter((s) => s.page > 0)
	);
	let at = $state(0);
	const onPage = $derived(drawn.filter((s) => s.page === (at || page)));

	/** What `locate` answers beside the usual result line: the anchor loom would record, and the line a person reads. */
	interface Located {
		anchor?: Record<string, unknown>;
		text?: string;
	}

	async function locate(body: Record<string, unknown>): Promise<void> {
		told = 'asking loom…';
		const res: WriteResult & Located = await write('locate', { citekey, ...body });
		told = res.ok ? `${res.result}\n${JSON.stringify(res.anchor)}` : `refused: ${res.error?.message ?? ''}`;
	}

	// Three states, not two. A work whose LaTeX is in the store but whose PDF is not has a digest worth trusting and no
	// page to show it against, which is neither "nothing here" nor "we could not get it" — and page-numbered locators
	// into it are unverified, because the pagination a reader will open is the publisher's and not ours.
	const absent = $derived(
		ref.unreadable
			? `Declared unreadable: ${ref.unreadable.why}`
			: ref.artifacts?.source
				? 'The LaTeX of this paper is here but its PDF is not, so there is no page to show. Locators into it are unverified against the document a reader would open.'
				: 'No copy of this paper on this machine.'
	);

	function travel(e: { id: string; travel: boolean }): void {
		active = e.id;
		if (!e.travel) return;
		document
			.querySelector(`[data-anchored="${CSS.escape(e.id)}"]`)
			?.scrollIntoView({ behavior: 'smooth', block: 'center' });
	}
</script>

<section class="reading" data-testid="reading">
	<Split contentLabel="the paper" discussionLabel="anchored">
		{#snippet content()}
			{#if url}
				<PdfDoc
					{url}
					{page}
					spans={drawn}
					focus={active}
					onselect={(e) => locate({ page: e.page, text: e.text })}
					onbox={(e) => locate({ page: e.page, rects: e.rects })}
					onmark={travel}
					onpage={(e) => (at = e.page)}
				/>
			{:else}
				<p class="muted" data-testid="reading-absent">{absent}</p>
			{/if}
		{/snippet}
		{#snippet discussion()}
			<div class="stack">
			<aside class="beside">
				<h2>Anchored to page {at || page}</h2>
				{#each onPage as q (q.id)}
					<article data-anchored={q.id} data-testid="anchored-{q.id}" class:active={active === q.id}>
						<h3>{q.id}</h3>
						<p>{ref.results?.[q.id]?.source_text ?? ''}</p>
					</article>
				{:else}
					<p class="muted">Nothing is anchored to this page.</p>
				{/each}
				{#if told}<pre class="told" data-testid="located">{told}</pre>{/if}
			</aside>
			<!-- docked in the discussion pane's foot, which is where a reply to what is beside it belongs -->
			<Composer />
			</div>
		{/snippet}
	</Split>
</section>

<style>
	.reading {
		height: 78vh;
		min-height: 320px;
		margin: 16px 0;
		border: 1px solid var(--rule, #ddd9cf);
	}
	.stack {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.beside {
		flex: 1 1 auto;
		overflow: auto;
		padding: 8px 12px;
		font-size: 0.9rem;
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
	}
	article {
		border-top: 1px solid var(--rule, #ddd9cf);
		padding: 8px 0;
	}
	article.active {
		background: var(--annotation-tint, rgb(217 119 87 / 0.14));
	}
	h3 {
		margin: 0 0 4px;
		font-size: 0.8rem;
	}
	p {
		margin: 0;
	}
	.told {
		margin-top: 12px;
		font-size: 0.72rem;
		white-space: pre-wrap;
		word-break: break-all;
	}
</style>
