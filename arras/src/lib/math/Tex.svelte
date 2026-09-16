<script lang="ts">
	// A title that carries inline math, typeset in place. Titles keep their LaTeX rather than losing it (a section called `Structure of $\Sigma$` used to arrive as `Structure of $ $`), so wherever a title is shown as prose it goes through here.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';

	let { text }: { text: string } = $props();

	let el: HTMLElement | undefined = $state();
	const hasMath = $derived(/\$[^$]*\$/.test(text));

	// MathJax's inline delimiters here are \( \), matching what the publisher emits, so a title's dollars are translated before typesetting.
	const prepared = $derived(hasMath ? text.replace(/\$([^$]*)\$/g, (_, m: string) => '\\(' + m + '\\)') : text);

	$effect(() => {
		const node = el;
		const t = prepared;
		if (!node || !hasMath) return;
		node.textContent = t;
		void typeset(node, store.manifest?.macros.default ?? []);
	});
</script>

{#if hasMath}<span bind:this={el}>{prepared}</span>{:else}{text}{/if}
