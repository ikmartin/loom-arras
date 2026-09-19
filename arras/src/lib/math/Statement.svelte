<script lang="ts">
	// A statement as LaTeX source, typeset in place: a proposal's rendering, which nothing on the publisher has turned into a fragment yet.
	//
	// Titles go through `Tex.svelte`, which knows only inline `$…$`. A statement carries displays too, and Graber and Pandharipande's formula -- the one thing the proposal existed to record -- sat on the verification surface as raw `$$…$$` source. Line breaks are kept, since a statement's `(i)`, `(ii)` are laid out by them.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';
	import { delimit } from '$lib/math/delimit';

	let { text }: { text: string } = $props();

	let el: HTMLElement | undefined = $state();

	$effect(() => {
		const node = el;
		const t = delimit(text);
		if (!node) return;
		node.textContent = t;
		void typeset(node, store.manifest?.macros.default ?? []);
	});
</script>

<span class="statement" bind:this={el}>{delimit(text)}</span>

<style>
	.statement {
		white-space: pre-line;
	}
</style>
