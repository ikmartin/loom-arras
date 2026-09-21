<script lang="ts">
	// The delete confirmation (plan 0.13.1, §18's mockup). A browser `confirm()` stood here, which could not say the one
	// thing that decides the answer: **how much is still open in the session about to go**. It also could not offer the
	// escape hatch, since purging is deliberately terminal-only and the sentence naming it is the only place a reader
	// learns it exists.
	import { dismiss } from '$lib/dismiss';

	let {
		title,
		open,
		onCancel,
		onDelete
	}: { title: string; open: number; onCancel: () => void; onDelete: () => void } = $props();

	let box = $state<HTMLDivElement | null>(null);
	$effect(() => box?.querySelector<HTMLButtonElement>('[data-testid=delete-confirm]')?.focus());
</script>

<div class="scrim" role="presentation">
	<div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-title" data-testid="delete-session" bind:this={box} use:dismiss={onCancel}>
		<h3 id="delete-title">Delete “{title}”?</h3>
		{#if open > 0}
			<p data-testid="delete-open">
				<strong>{open} annotation{open === 1 ? ' is' : 's are'} still OPEN.</strong> Are you sure you want to delete this session?
			</p>
		{:else}
			<p data-testid="delete-open">Nothing in it is still open. Are you sure you want to delete this session?</p>
		{/if}
		<p>The session is removed from view. What was written stays in the log; <code>loom session delete --purge</code> erases it for good.</p>
		<div class="buttons">
			<button type="button" data-testid="delete-cancel" onclick={onCancel}>Cancel</button>
			<button type="button" class="destroy" data-testid="delete-confirm" onclick={onDelete}>Delete</button>
		</div>
	</div>
</div>

<style>
	.scrim {
		position: fixed;
		inset: 0;
		background: rgb(44 44 42 / 0.55);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--gap);
		z-index: 60;
	}
	.modal {
		background: var(--sheet);
		border-radius: var(--rad-card);
		box-shadow: 0 18px 50px rgb(0 0 0 / 28%);
		padding: var(--gap-wide);
		max-width: 460px;
		width: 100%;
	}
	h3 {
		margin: 0 0 var(--gap);
		font-family: var(--serif);
		font-size: 21px;
		font-weight: 400;
		text-wrap: balance;
	}
	p {
		margin: 0 0 var(--gap);
		font-size: 14px;
		line-height: 1.5;
		color: var(--ink-soft);
	}
	p strong {
		color: var(--ink);
	}
	code {
		font-size: 12.5px;
		background: var(--leaf);
		padding: 1px 4px;
		border-radius: var(--rad-pill);
	}
	.buttons {
		display: flex;
		justify-content: flex-end;
		gap: var(--gap-tight);
		margin-top: var(--gap-wide);
	}
	button {
		font: inherit;
		font-size: 14px;
		padding: 7px 16px;
		border-radius: var(--rad-control);
		cursor: pointer;
		border: 1px solid var(--rule);
		background: var(--sheet);
		color: var(--ink);
	}
	button:hover {
		border-color: var(--rule-strong);
	}
	.destroy {
		background: var(--state-incomplete);
		border-color: var(--state-incomplete);
		color: #fff;
		font-weight: 500;
	}
</style>
