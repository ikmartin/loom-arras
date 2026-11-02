<script lang="ts">
	// One setting: its name, what it does and where it is written on the left, its control on the right, or beneath with `stack` for a list. The words are the catalog's.
	import type { Snippet } from 'svelte';
	import { SETTING } from './catalog';
	import Words from './Words.svelte';

	let { id, stack = false, refused = '', children }: { id: string; stack?: boolean; refused?: string; children?: Snippet } = $props();
	const s = $derived(SETTING[id]);
</script>

<div class="set" class:stack data-testid="setting-{id}">
	<div class="about">
		<div class="name">{s.name}</div>
		<div class="what"><Words text={s.what} /></div>
		{#if s.key}<div class="key">{s.key}</div>{/if}
		{#if refused}<p class="refused" role="alert" data-testid="setting-refused">{refused}</p>{/if}
		{#if stack}{@render children?.()}{/if}
	</div>
	{#if !stack}<div class="control">{@render children?.()}</div>{/if}
</div>

<style>
	.set {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 18px;
		align-items: center;
		padding: 14px 16px;
		border-top: 1px solid var(--rule);
	}
	.set:first-child {
		border-top: 0;
	}
	.set.stack {
		grid-template-columns: minmax(0, 1fr);
	}
	.name {
		font-size: 14px;
		font-weight: 500;
		color: var(--ink);
	}
	.what {
		font-size: 12.5px;
		color: var(--ink-soft);
		margin-top: 3px;
		line-height: 1.45;
	}
	.key {
		font-family: var(--mono);
		font-size: 11px;
		color: var(--ink-faint);
		margin-top: 4px;
	}
	.refused {
		margin: 6px 0 0;
		font-size: 12.5px;
		color: var(--state-conflicted);
	}
	.control {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	/* a narrow window puts the control under its words */
	@media (max-width: 560px) {
		.set {
			grid-template-columns: minmax(0, 1fr);
			gap: 10px;
		}
	}
</style>
