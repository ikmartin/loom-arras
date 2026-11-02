<script lang="ts">
	// Suggestions (plan 0.22.8): every open suggestion, with the words it is on, the text it proposes and the patch that takes it, each linking to its place in its document, where it is shown in place. Applying one is the author's; the publisher sees the key read as the suggestion taken and resolves it as applied.
	import DiffView from '$lib/components/DiffView.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import { openSuggestions } from '$lib/review/sections';
	import { keyName } from '$lib/workspace/names';

	const m = $derived(store.manifest!);
	const open = $derived(openSuggestions(m).sort((a, b) => (b.created ?? '').localeCompare(a.created ?? '')));
</script>

<main class="page scrollbar-shown" data-testid="suggestions">
	<h1>Suggestions</h1>
	<p class="lead">What someone proposed changing, waiting to be applied. Each opens in place, with the change shown, and the patch that takes it is here.</p>
	{#if !open.length}
		<p class="muted" data-testid="suggestions-none">No suggestion is waiting.</p>
	{:else}
		<ul class="plain">
			{#each open as a (a.id)}
				<li class="suggestion" data-testid="suggestion">
					<a href="quilt:{a.id}">{keyName(m, a.target.key)}</a>
					<span class="faint">· {a.author?.id ?? ''}{a.severity ? ` · ${a.severity}` : ''}</span>
					{#if a.quote}<q class="quoted">{a.quote}</q>{/if}
					{#if a.payload}<pre class="payload">{a.payload}</pre>{/if}
					<Prose html={a.body_html} />
					{#if a.change?.state === 'ready'}<DiffView path={a.change.diff} />{/if}
				</li>
			{/each}
		</ul>
	{/if}
</main>

<style>
	.suggestion {
		margin: var(--gap) 0;
		padding-bottom: var(--gap);
		border-bottom: 1px solid var(--rule);
	}
	.payload {
		white-space: pre-wrap;
		font-family: var(--mono);
		font-size: 12.5px;
		background: var(--sheet);
		padding: var(--gap-hair) var(--gap-tight);
	}
</style>
