<script lang="ts">
	// A snippet of LaTeX prose rendered as prose: the math typeset, and the handful of text commands a written sentence
	// actually uses turned into the markup they mean.
	//
	// It is not a LaTeX engine and does not pretend to be one. loom renders documents; this renders the sentence or two
	// an annotation proposes, which arrive as prose with inline math and the occasional `\emph`. Anything it does not
	// know is left exactly as written, so what is on screen is never a silent misreading of what was proposed -- a
	// reader who sees a command still in its braces knows to read the verbatim instead.
	import { store } from '$lib/manifest/client.svelte';
	import { typeset } from '$lib/math/mathjax';

	let { text }: { text: string } = $props();

	let el: HTMLElement | undefined = $state();

	const ESC: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;' };

	/** The text commands a proposed sentence uses. Everything else stays literal. */
	const MARKUP: [RegExp, string, string][] = [
		[/\\emph\{([^{}]*)\}/g, '<em>', '</em>'],
		[/\\textit\{([^{}]*)\}/g, '<em>', '</em>'],
		[/\\textbf\{([^{}]*)\}/g, '<strong>', '</strong>'],
		[/\\texttt\{([^{}]*)\}/g, '<code>', '</code>']
	];

	/** A cross-reference as the reader's documents print it: the default document's number, else the result's title, else the key. MathJax would otherwise turn a `\ref` outside math into `???`. */
	function refText(key: string, eq: boolean): string {
		const m = store.manifest;
		const main = m?.masters.find((x) => x.default)?.path ?? '';
		const n = m?.nodes[key];
		const num = n?.numbers[main]?.number ?? m?.regions?.[key]?.numbers[main]?.number;
		const said = num ?? n?.title ?? key;
		return eq ? `(${said})` : said;
	}

	// Escaped first, so the only markup in the result is the markup this file put there.
	const html = $derived.by(() => {
		let out = text
			.replace(/\\(eq)?ref\{([^{}]*)\}/g, (_, eq: string | undefined, key: string) => refText(key.trim(), !!eq))
			.replace(/~/g, '\u00a0')
			.replace(/[&<>]/g, (c) => ESC[c]);
		for (const [re, open, close] of MARKUP) out = out.replace(re, (_, inner: string) => open + inner + close);
		// MathJax's inline delimiters here are \( \), matching what the publisher emits
		return out.replace(/\$([^$]*)\$/g, (_, m: string) => '\\(' + m + '\\)');
	});

	$effect(() => {
		const node = el;
		const h = html;
		if (!node) return;
		node.innerHTML = h;
		void typeset(node, store.manifest?.macros.default ?? []);
	});
</script>

<span bind:this={el}></span>
