<script lang="ts">
	// Why a write is unavailable, said where the write would have happened (plan 0.13.1).
	//
	// **The control is greyed and the reason is on demand.** A disabled button that explains itself in a permanent line
	// of text would put the same sentence beside every composer on the page; a disabled button that explains nothing
	// leaves the reader guessing which of the two problems they have. So the control stays disabled, pressing it does
	// nothing but raise this, and it goes again on its own.
	import { store } from '$lib/manifest/client.svelte';
	import { writable } from './sessions.svelte';

	let { placement = 'above' }: { placement?: 'above' | 'below' } = $props();

	const why = $derived(writable(store.manifest));
	let shown = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	/** Raise the tip for a moment. Called by a write surface when a disabled control was pressed anyway. */
	export function say(): void {
		if (!why) return;
		shown = true;
		clearTimeout(timer);
		timer = setTimeout(() => (shown = false), 4000);
	}

	/** Whether a write is allowed at all, for a caller deciding whether to disable its control. */
	export function blocked(): string {
		return why;
	}
</script>

{#if shown && why}
	<p class="tip" class:below={placement === 'below'} role="status" data-testid="no-session-tip">{why}</p>
{/if}

<style>
	.tip {
		position: absolute;
		bottom: calc(100% + 8px);
		left: 0;
		z-index: 30;
		max-width: 340px;
		margin: 0;
		background: var(--ink);
		color: var(--leaf);
		font-family: var(--sans);
		font-size: 12.5px;
		line-height: 1.4;
		padding: 8px 11px;
		border-radius: var(--rad-control);
		box-shadow: 0 6px 18px rgb(0 0 0 / 22%);
	}
	.tip.below {
		bottom: auto;
		top: calc(100% + 8px);
	}
	.tip::after {
		content: '';
		position: absolute;
		top: 100%;
		left: 18px;
		border: 6px solid transparent;
		border-top-color: var(--ink);
	}
	.tip.below::after {
		top: auto;
		bottom: 100%;
		border-top-color: transparent;
		border-bottom-color: var(--ink);
	}
</style>
