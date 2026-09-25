<script lang="ts">
	// Reading a text as it was written rather than as it renders (plan 0.11 Part E).
	//
	// The control appears only where there is something behind it: a corpus that publishes no source shows nothing at all, rather than a button that explains itself by failing. It names what a click gives you rather than what is on screen, so the reader picks a view instead of decoding a state.
	//
	// It used to carry `copy` and `copy for chat` beside it. Both are gone: selecting the text is how anyone copies text, the second wrapped it in a tag syntax nobody asked for, and three controls where one was wanted is what made the row unreadable when it was narrow.
	import { fetchSource } from '$lib/source';

	let {
		sourceKey,
		text = null,
		open = $bindable(false)
	}: {
		/** The key whose source to fetch. Ignored when `text` is given. */
		sourceKey: string;
		/** Source already in hand, for a payload, which the manifest carries. */
		text?: string | null;
		open?: boolean;
	} = $props();

	let fetched = $state<string | null>(null);
	let tried = $state(false);

	const body = $derived(text ?? fetched);

	$effect(() => {
		if (text !== null || tried) return;
		tried = true;
		fetchSource(sourceKey).then((s) => (fetched = s));
	});

</script>

{#if body}
	<span class="tools" data-testid="source-tools">
		<button class:on={open} onclick={() => (open = !open)} aria-pressed={open} data-testid="source-toggle">
			{open ? 'rendered latex' : 'verbatim code'}
		</button>
	</span>
{/if}

{#if open && body}
	<pre class="verbatim" data-testid="verbatim" aria-label="the LaTeX behind this block">{body}</pre>
{/if}

<style>
	.tools {
		display: inline-flex;
		gap: 0.4em;
		align-items: baseline;
		font-family: var(--sans);
		font-size: 0.72em;
		/* Out of the way until wanted, but never hidden from a keyboard: focus-within is what keeps tabbing through the page from stepping into something invisible. */
		opacity: 0.25;
		transition: opacity 120ms ease;
	}
	.tools:hover,
	.tools:focus-within {
		opacity: 1;
	}
	.tools button {
		background: none;
		border: 1px solid var(--rule);
		border-radius: 2px;
		padding: 0 0.4em;
		font: inherit;
		color: var(--ink-soft);
		cursor: pointer;
	}
	.tools button.on {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
	.verbatim {
		white-space: pre-wrap;
		overflow-x: auto;
		font-size: 0.85em;
		line-height: 1.5;
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		padding: var(--gap);
		margin: var(--gap-tight) 0 0;
	}
</style>
