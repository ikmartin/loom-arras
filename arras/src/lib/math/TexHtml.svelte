<script lang="ts">
	// Markup the publisher rendered from TeX, typeset: a proposal read the way the document would print it, theorem and proof included, where TexProse knows only a sentence.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';

	let { html }: { html: string } = $props();

	let el: HTMLElement | undefined = $state();

	$effect(() => {
		const node = el;
		const h = html;
		if (!node) return;
		node.innerHTML = h;
		void typeset(node, store.manifest?.macros.default ?? []);
	});
</script>

<div bind:this={el}></div>
