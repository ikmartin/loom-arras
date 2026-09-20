<script lang="ts">
	// Reading a text as it was written rather than as it renders (plan 0.11 Part E).
	//
	// The control appears only where there is something behind it: a corpus that publishes no source shows nothing at all, rather than a button that explains itself by failing. Copy is beside it because reading the source and taking it somewhere are the same errand -- usually into a conversation with an agent, which is what "copy for chat" is for.
	import { copyText } from '$lib/clipboard';
	import { fetchSource, forChat } from '$lib/source';

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
	let said = $state('');

	const body = $derived(text ?? fetched);

	$effect(() => {
		if (text !== null || tried) return;
		tried = true;
		fetchSource(sourceKey).then((s) => (fetched = s));
	});

	async function copy(what: 'plain' | 'chat') {
		if (!body) return;
		const ok = await copyText(what === 'chat' ? forChat(sourceKey, body) : body);
		said = ok ? 'copied' : 'could not copy';
		setTimeout(() => (said = ''), 1600);
	}
</script>

{#if body}
	<span class="tools" data-testid="source-tools">
		<button class:on={open} onclick={() => (open = !open)} aria-pressed={open} data-testid="source-toggle">
			{open ? 'rendered' : 'source'}
		</button>
		<button onclick={() => copy('plain')} data-testid="source-copy">copy</button>
		<button onclick={() => copy('chat')} title="the key in the author's tag syntax, then the text" data-testid="source-copy-chat">copy for chat</button>
		{#if said}<span class="said" role="status">{said}</span>{/if}
	</span>
{/if}

{#if open && body}
	<pre class="verbatim" data-testid="verbatim">{body}</pre>
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
	.said {
		color: var(--ink-faint);
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
