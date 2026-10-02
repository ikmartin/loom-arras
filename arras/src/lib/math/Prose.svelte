<script lang="ts">
	// A body of published prose — an annotation, a reply, a chat message — rendered and typeset, with every `quilt:` or `cited:` link written with no text named as the viewer names what it points at (plan 0.14).
	//
	// The publisher writes mathematics into these bodies as the dialect's `<span class="math inline">\(…\)</span>`, the same markup a node fragment carries, but nothing ran MathJax over them: `{@html body_html}` put the delimiters on the page as literal text, so every `$…$` an author or an agent typed arrived as `\(n \le 2\)`. Fragments go through `Fragment.svelte` and titles through `Tex.svelte`; this is the third place published TeX appears and the one that had no typesetter.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';
	import { linkName } from '$lib/workspace/names';
	import { linkIds } from './ids';

	let { html, class: klass = 'body' }: { html: string; class?: string } = $props();

	let el: HTMLElement | undefined = $state();

	// An empty link is named by the viewer, so the name is the one a reader uses and stays right when the document is renumbered. A bare id in the prose — an agent writes `rl-0020-ai(a)` as often as a link — becomes such a link first, where the manifest knows it.
	$effect(() => {
		const node = el;
		const m = store.manifest;
		void html;
		if (!node || !m) return;
		linkIds(node, (key) => !!m.nodes[key]);
		for (const a of node.querySelectorAll<HTMLAnchorElement>('a[href^="quilt:"], a[href^="cited:"]')) {
			if (!a.textContent?.trim()) a.textContent = linkName(m, a.getAttribute('href') ?? '');
		}
	});

	$effect(() => {
		const node = el;
		const body = html; // re-typeset when the body is superseded by an edit
		if (!node || !body.includes('class="math')) return;
		void typeset(node, store.manifest?.macros.default ?? []);
	});
</script>

<div class={klass} bind:this={el}>{@html html}</div>

<style>
	/* A table an author or an agent writes in Markdown (a comparison, a list of citations against the draft) — ruled like the viewer's own tables, and scrolled within itself rather than widening the column when it is wider than the prose. */
	div :global(table) {
		display: block;
		max-width: 100%;
		overflow-x: auto;
		border-collapse: collapse;
		margin: var(--gap-tight) 0;
		font-size: 0.92em;
	}
	div :global(th),
	div :global(td) {
		text-align: left;
		vertical-align: top;
		padding: var(--gap-hair) var(--gap-tight);
		border-bottom: 1px solid var(--rule);
	}
	div :global(th) {
		font-weight: 600;
		border-bottom-color: var(--rule-strong);
	}
</style>
