<script lang="ts">
	// A list setting's entries, each removable unless `remove` is absent; `fixed` ones are shown and never removed.
	let { items, remove, fixed = false, test }: { items: string[]; remove?: (item: string) => void; fixed?: boolean; test: string } = $props();
</script>

{#if items.length}
	<div class="chips" data-testid={test}>
		{#each items as item (item)}
			<span class="chip" class:fixed>{item}{#if remove && !fixed}<button aria-label="Remove {item}" onclick={() => remove(item)}>×</button>{/if}</span>
		{/each}
	</div>
{/if}

<style>
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 8px;
	}
	.chip {
		font-family: var(--mono);
		font-size: 12px;
		padding: 4px 10px;
		border-radius: 7px;
		background: var(--leaf);
		border: 1px solid var(--rule);
		display: inline-flex;
		align-items: center;
		gap: 6px;
		overflow-wrap: anywhere;
	}
	.chip.fixed {
		color: var(--ink-faint);
		border-style: dashed;
	}
	button {
		font: inherit;
		border: 0;
		background: none;
		color: var(--ink-faint);
		cursor: pointer;
		padding: 0 2px;
	}
	button:hover {
		color: var(--ink);
	}
</style>
