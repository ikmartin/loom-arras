<script lang="ts">
	// The mark after a row's name in the project's tree: "AI" where agents edit it too, "AI" struck through where only the person does. It only says; the deny list changes in Settings. Its meaning opens beside it under the pointer or the focus, and on a press for a hand with no pointer.
	import Popover from '$lib/components/Popover.svelte';
	import type { Explained } from './access';

	let { agents, said, testid }: { agents: boolean; said: Explained; testid?: string } = $props();

	let open = $state(false);
	let wait = 0;
	// a pointer passing down the tree on its way elsewhere opens nothing
	function soon(): void {
		clearTimeout(wait);
		wait = window.setTimeout(() => (open = true), 150);
	}
	function shut(): void {
		clearTimeout(wait);
		open = false;
	}
</script>

<Popover bind:open placement="right" width={260} role="tooltip" testid={testid ? `${testid}-says` : undefined}>
	{#snippet trigger({ toggle })}
		<button
			type="button"
			class="mark"
			class:off={!agents}
			aria-label={said.title}
			aria-expanded={open}
			data-testid={testid}
			data-agents={agents ? 'yes' : 'no'}
			onmouseenter={soon}
			onmouseleave={shut}
			onfocus={soon}
			onblur={shut}
			onclick={toggle}>AI</button
		>
	{/snippet}
	<div class="says">
		<p class="title">{said.title}</p>
		<p>{said.body}</p>
	</div>
</Popover>

<style>
	.mark {
		all: unset;
		margin-left: 0.4em;
		padding: 0 3px;
		border-radius: 3px;
		font-family: var(--sans);
		font-size: 9.5px;
		font-weight: 600;
		letter-spacing: 0.02em;
		line-height: 13px;
		vertical-align: 1px;
		color: var(--agent);
		cursor: default;
	}
	.mark:focus-visible {
		box-shadow: 0 0 0 1px var(--link);
	}
	/* struck through on the diagonal, as a sign is crossed out, the stroke stopping short of the corners */
	.mark.off {
		color: var(--ink-faint);
		background: linear-gradient(to top right, transparent calc(50% - 0.6px), currentColor calc(50% - 0.6px), currentColor calc(50% + 0.6px), transparent calc(50% + 0.6px)) center / 72% 78% no-repeat;
	}
	.says {
		padding: var(--gap-tight) var(--gap);
		font-family: var(--sans);
		font-size: 11.5px;
		line-height: 1.5;
		color: var(--ink-soft);
	}
	.says p {
		margin: 0;
	}
	.says .title {
		color: var(--ink);
		font-weight: 600;
		margin-bottom: 2px;
	}
</style>
