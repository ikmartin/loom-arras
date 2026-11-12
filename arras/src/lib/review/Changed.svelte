<script lang="ts">
	// The line under the look controls while a look differs from its type's: "Changed from Revision", Reset to the type's look, and Update the type to this look where the publisher saves types.
	let {
		name,
		disabled = false,
		onreset,
		onupdate
	}: {
		/** The type's own name. */
		name: string;
		disabled?: boolean;
		onreset: () => void;
		/** Write this look into the type; absent where types cannot be saved. */
		onupdate?: () => void;
	} = $props();
</script>

<div class="modline" data-testid="modified-line">
	<span>Changed from {name}</span>
	<button type="button" class="lnk" {disabled} data-testid="modified-reset" onclick={onreset}>Reset</button>
	{#if onupdate}<button type="button" class="lnk" {disabled} data-testid="modified-update" onclick={onupdate}>Update {name}</button>{/if}
</div>

<style>
	.modline {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 4px 12px;
		font-family: var(--sans);
		font-size: 12px;
		color: var(--ink-soft);
	}
	.modline span {
		margin-right: auto;
	}
	.lnk {
		padding: 0;
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.lnk:hover:not(:disabled) {
		text-decoration: underline;
	}
	.lnk:disabled {
		opacity: 0.5;
		cursor: default;
	}
</style>
