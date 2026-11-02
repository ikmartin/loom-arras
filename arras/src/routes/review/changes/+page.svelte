<script lang="ts">
	// Changes (plan 0.22.8): what changed in the open files since the reviewer's look, each file with its diff, kept or undone. Keeping takes the file's text now into the look; undoing puts the text at the look back, and loom keeps the text it replaces in the history first. Who made a change is not said, since loom cannot know it. Both verbs are the author's, and say nothing about whether the mathematics is right, which is what Needs review is for.
	import DiffView from '$lib/components/DiffView.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { can, write } from '$lib/write';
	import { onMount } from 'svelte';

	const m = $derived(store.manifest!);
	const changes = $derived(m.changes ?? []);
	const since = $derived(m.changes_since);
	let acts = $state(false);
	let busy = $state('');
	let said = $state('');
	onMount(() => {
		void can('changes-keep').then((yes) => (acts = yes));
	});

	const WHAT: Record<string, string> = { changed: 'changed', new: 'new since your look', gone: 'gone since your look' };

	async function act(endpoint: 'changes-keep' | 'changes-undo', path?: string): Promise<void> {
		busy = path ?? '*';
		said = '';
		const done = await write(endpoint, path ? { path } : {});
		busy = '';
		if (!done.ok) said = done.error?.message ?? 'the publisher refused it';
		else await store.refresh();
	}
</script>

<main class="page scrollbar-shown" data-testid="changes">
	<h1>Changes</h1>
	{#if !since}
		<p class="lead">Nothing to compare against yet: the publisher takes your first look at the open files when it starts.</p>
	{:else}
		<p class="lead">What changed in the open files since your look, {since.when.slice(0, 16).replace('T', ' ')}. Keep a change to take it into your look; undo it to put the file back as it was, its text now kept in the history. Neither says whether the mathematics is right.</p>
		{#if said}<p class="said" role="status" data-testid="changes-said">{said}</p>{/if}
		{#if !changes.length}
			<p class="muted" data-testid="changes-none">Nothing has changed since your look.</p>
		{:else}
			{#if acts}
				<p class="actions"><button onclick={() => act('changes-keep')} disabled={!!busy} data-testid="changes-keep-all">Keep all</button></p>
			{/if}
			{#each changes as c (c.path)}
				<section class="change" data-testid="change" data-path={c.path}>
					<h2><code>{c.path}</code> <span class="muted">{WHAT[c.kind] ?? c.kind}</span></h2>
					{#if acts}
						<p class="actions">
							<button onclick={() => act('changes-keep', c.path)} disabled={!!busy} data-testid="change-keep">Keep</button>
							{#if c.kind !== 'new'}
								<button onclick={() => act('changes-undo', c.path)} disabled={!!busy} data-testid="change-undo">Undo</button>
							{:else}
								<span class="faint">New since your look: keep it, or delete it yourself.</span>
							{/if}
						</p>
					{/if}
					{#if c.diff}<DiffView path={c.diff} />{/if}
				</section>
			{/each}
		{/if}
	{/if}
</main>

<style>
	.change {
		margin: var(--gap-wide) 0;
	}
	.change h2 {
		font-size: 13px;
		text-transform: none;
		letter-spacing: 0;
	}
	.actions {
		display: flex;
		gap: var(--gap-tight);
		align-items: center;
	}
	.said {
		color: var(--state-stale, #a33);
	}
</style>
