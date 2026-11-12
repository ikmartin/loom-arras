<script lang="ts">
	// The toast (`toasts.svelte.ts`): bottom centre, over everything, a click takes it down.
	import { toast, unsay } from './toasts.svelte';
</script>

<div class="live" role="status" aria-live="polite">
	{#if toast.said}
		<button type="button" class="toast" data-testid="toast" onclick={unsay}>
			<b>{toast.said.title}</b>
			{#if toast.said.words}<span class="tq">“{toast.said.words}”</span>{/if}
			{#each toast.said.lines as line, i (i)}<span class="tw">{line}</span>{/each}
		</button>
	{/if}
</div>

<style>
	.live {
		display: contents;
	}
	.toast {
		position: fixed;
		z-index: 70;
		left: 50%;
		bottom: calc(var(--gap) + 44px);
		transform: translateX(-50%);
		display: grid;
		gap: 3px;
		max-width: min(460px, calc(100vw - 32px));
		padding: 10px 14px;
		font-family: var(--sans);
		font-size: 12.5px;
		text-align: left;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule-strong);
		border-radius: var(--rad-control);
		box-shadow: var(--float-shadow);
		cursor: pointer;
	}
	.tq {
		font-family: var(--body-face);
		font-size: 14px;
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
	}
	.tw {
		color: var(--ink-soft);
	}
</style>
