<script lang="ts">
	// One block's or one file's edit since the look: its changes alone out of the file's diff, each with its own controls when it has several. Folded where a page lists many, so a long list costs nothing until one is asked for.
	import type { Snippet } from 'svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import type { Edit } from './yourText';

	let { edit, folded = false, hunk }: { edit: Edit; folded?: boolean; hunk?: Snippet<[number]> } = $props();
	let open = $state(false);
	const path = $derived(edit.change.diff);
	const several = $derived(edit.hunks.length > 1);
	// the file's text and how many changes it has left: keeping one moves the second alone
	const version = $derived(`${edit.change.hash}/${edit.change.hunks}`);
</script>

{#if path}
	{#if folded}
		<details class="fold" bind:open data-testid="edit-fold">
			<summary>See the edit</summary>
			{#if open}<DiffView {path} {version} only={edit.hunks} hunk={several ? hunk : undefined} />{/if}
		</details>
	{:else}
		<div class="edit"><DiffView {path} {version} only={edit.hunks} hunk={several ? hunk : undefined} /></div>
	{/if}
{/if}

<style>
	.edit,
	.fold {
		margin-top: 6px;
	}
	.fold summary {
		font-size: 12.5px;
		color: var(--ink-soft);
		cursor: pointer;
	}
</style>
