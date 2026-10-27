<script lang="ts">
	// `/` is reading where it was left: this visit's workspace, else the address remembered from an earlier visit, else the default document, else the newest landmark (`readingAddress`). A quilt with nothing to read opens on how to start instead: the publisher's `loom:no-live-document` advice and its fixes, one step each, each showing its command now, drawn from the fixes so that a step can become a control once the viewer can take it.
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { readingAddress } from '$lib/shell/views';
	import { rememberedIn } from '$lib/workspace/remember';
	import { workspace } from '$lib/workspace/store.svelte';

	const m = $derived(store.manifest!);
	const to = $derived(readingAddress(m, workspace.canonical(m) || rememberedIn(m)));
	$effect(() => {
		if (to) void goto(to, { replaceState: true, noScroll: true, keepFocus: true });
	});
	const advice = $derived(m.diagnostics.find((d) => d.code === 'loom:no-live-document'));
</script>

{#if !to}
	<main class="page start" data-testid="how-to-start">
		<h1>Nothing to read yet</h1>
		{#if advice}
			<p>{advice.message}</p>
			<ol class="steps">
				{#each advice.fixes ?? [] as f (f.command)}
					<li data-testid="start-step"><span>{f.label}</span><code>{f.command}</code></li>
				{/each}
			</ol>
		{/if}
	</main>
{/if}

<style>
	.start {
		max-width: 40rem;
	}
	.steps {
		display: grid;
		gap: var(--gap-tight);
		padding-left: 1.2em;
	}
	.steps li {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 12px;
	}
	.steps code {
		font-size: 0.9em;
	}
</style>
