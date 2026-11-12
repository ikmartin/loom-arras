<script lang="ts">
	// The Type list: No type, then the quilt's types in their order, each with a sample in its look and its number key, then the way to add one. What a row shows is the type's own name and look and nothing else.
	import type { AnnotationType, Look } from '$lib/manifest/types';
	import Sample from './Sample.svelte';

	let {
		types,
		current,
		look,
		keys = false,
		disabled = false,
		onpick,
		onadd
	}: {
		types: AnnotationType[];
		/** The type chosen; null for none. */
		current: string | null;
		/** The look shown beside No type: what is held now. */
		look: Look;
		/** Show each row's number key. */
		keys?: boolean;
		disabled?: boolean;
		onpick: (id: string | null) => void;
		/** Add a type, in Settings; absent where types cannot be written. */
		onadd?: () => void;
	} = $props();
</script>

<div class="tlist" role="listbox" aria-label="Type" data-testid="type-list">
	<div class="tscroll">
		<button type="button" class="trow" class:on={current === null} role="option" aria-selected={current === null} title="Keep the look, with no type" {disabled} data-testid="type-none" onclick={() => onpick(null)}><Sample {look} /><span class="tn">No type</span>{#if keys}<kbd>0</kbd>{/if}</button>
		{#each types as t, i (t.id)}
			<button type="button" class="trow" class:on={current === t.id} role="option" aria-selected={current === t.id} {disabled} data-testid="type-row" data-type={t.id} onclick={() => onpick(t.id)}><Sample look={t.look} /><span class="tn">{t.name}</span>{#if keys && i < 9}<kbd>{i + 1}</kbd>{/if}</button>
		{/each}
	</div>
	{#if onadd}<button type="button" class="trow add" {disabled} data-testid="type-add" onclick={onadd}>+ Add new…</button>{/if}
</div>

<style>
	.tlist {
		display: grid;
		gap: 2px;
		font-family: var(--sans);
		font-size: 12.5px;
	}
	.tscroll {
		display: grid;
		gap: 1px;
		max-height: 190px;
		overflow-y: auto;
	}
	.trow {
		display: grid;
		grid-template-columns: 30px 1fr auto;
		align-items: center;
		gap: 8px;
		width: 100%;
		box-sizing: border-box;
		padding: 4px 8px;
		font: inherit;
		color: var(--ink);
		text-align: left;
		background: none;
		border: 0;
		border-radius: 6px;
		cursor: pointer;
	}
	.trow:hover:not(:disabled) {
		background: var(--leaf);
	}
	.trow.on {
		background: var(--accent-wash);
	}
	.trow.add {
		display: block;
		color: var(--ink-soft);
	}
	.tn {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	kbd {
		font-family: var(--sans);
		font-size: 10.5px;
		color: var(--ink-faint);
		border: 1px solid var(--rule);
		border-radius: 4px;
		padding: 0 5px;
	}
</style>
