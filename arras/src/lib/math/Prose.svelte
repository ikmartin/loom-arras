<script lang="ts">
	// A body of published prose — an annotation, a reply, a chat message — rendered and typeset, with every `quilt:` or `cited:` link written with no text named as the viewer names what it points at (plan 0.14).
	//
	// The publisher writes mathematics into these bodies as the dialect's `<span class="math inline">\(…\)</span>`, the same markup a node fragment carries, but nothing ran MathJax over them: `{@html body_html}` put the delimiters on the page as literal text, so every `$…$` an author or an agent typed arrived as `\(n \le 2\)`. Fragments go through `Fragment.svelte` and titles through `Tex.svelte`; this is the third place published TeX appears and the one that had no typesetter.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';
	import { linkName } from '$lib/workspace/names';

	let { html, class: klass = 'body' }: { html: string; class?: string } = $props();

	let el: HTMLElement | undefined = $state();

	// An empty link is named by the viewer, so the name is the one a reader uses and stays right when the document is renumbered.
	$effect(() => {
		const node = el;
		const m = store.manifest;
		void html;
		if (!node || !m) return;
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
