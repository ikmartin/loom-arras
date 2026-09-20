<script lang="ts">
	// A body of published prose — an annotation, a reply, a thread message — rendered and typeset.
	//
	// The publisher writes mathematics into these bodies as the dialect's `<span class="math inline">\(…\)</span>`, the same markup a node fragment carries, but nothing ran MathJax over them: `{@html body_html}` put the delimiters on the page as literal text, so every `$…$` an author or an agent typed arrived as `\(n \le 2\)`. Fragments go through `Fragment.svelte` and titles through `Tex.svelte`; this is the third place published TeX appears and the one that had no typesetter.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';

	let { html, class: klass = 'body' }: { html: string; class?: string } = $props();

	let el: HTMLElement | undefined = $state();

	$effect(() => {
		const node = el;
		const body = html; // re-typeset when the body is superseded by an edit
		if (!node || !body.includes('class="math')) return;
		void typeset(node, store.manifest?.macros.default ?? []);
	});
</script>

<div class={klass} bind:this={el}>{@html html}</div>
