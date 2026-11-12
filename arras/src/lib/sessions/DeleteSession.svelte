<script lang="ts">
	// The delete confirmation (plan 0.13.1, §18's mockup): what deleting a session does and does not touch, and the escape hatch, since purging is deliberately terminal-only and the sentence naming it is the only place a reader learns it exists.
	import Popover from '$lib/components/Popover.svelte';

	let { title, onCancel, onDelete }: { title: string; onCancel: () => void; onDelete: () => void } = $props();

	let box = $state<HTMLDivElement | null>(null);
	$effect(() => box?.querySelector<HTMLButtonElement>('[data-testid=delete-confirm]')?.focus());
</script>

<Popover modal open testid="delete-session" label="Delete “{title}”?" onclose={onCancel}>
	<div class="modal" bind:this={box}>
		<h3 id="delete-title">Delete “{title}”?</h3>
		<p>Are you sure you want to delete this session?</p>
		<p data-testid="delete-says">The session is removed from view. Annotations belong to no session, so none goes with it; <code>loom session delete --purge</code> erases its transcript for good.</p>
		<div class="buttons">
			<button type="button" data-testid="delete-cancel" onclick={onCancel}>Cancel</button>
			<button type="button" class="destroy" data-testid="delete-confirm" onclick={onDelete}>Delete</button>
		</div>
	</div>
</Popover>

<style>
	.modal {
		padding: var(--gap-wide);
		width: min(460px, 100%);
		box-sizing: border-box;
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
