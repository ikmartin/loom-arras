<script lang="ts">
	// One line of a toolbar's *view* menu (book 15.2.5): the control in full words, its key beside it where it has one. A mode is a `menuitemcheckbox` whose words name what a click gives; an action is a `menuitem`, a link where it opens a file. One that cannot act now stays in its place, greyed, with the reason as its title (DR-254-ikmartin).
	let {
		label,
		name,
		key,
		checked,
		href,
		off,
		testid,
		onclick
	}: {
		/** What a click gives, in full words. */
		label: string;
		/** The accessible name: the words and the item they act on. */
		name: string;
		/** The key that does the same from inside the document. */
		key?: string;
		/** Whether the mode is on; omitted for an action. */
		checked?: boolean;
		/** A file the item opens, in a new tab. */
		href?: string;
		/** Why it cannot act now. */
		off?: string;
		testid?: string;
		onclick?: () => void;
	} = $props();
</script>

{#if href && !off}
	<a class="item" role="menuitem" tabindex="-1" {href} target="_blank" rel="noopener" aria-label={name} data-testid={testid}><span class="lab">{label}</span></a>
{:else}
	<button
		type="button"
		class="item"
		role={checked === undefined ? 'menuitem' : 'menuitemcheckbox'}
		tabindex="-1"
		aria-checked={checked}
		aria-disabled={off ? 'true' : undefined}
		aria-label={name}
		aria-keyshortcuts={key}
		title={off}
		data-testid={testid}
		onclick={() => !off && onclick?.()}><span class="lab">{label}</span>{#if key}<kbd aria-hidden="true">{key}</kbd>{/if}</button
	>
{/if}

<style>
	.item {
		display: flex;
		width: 100%;
		box-sizing: border-box;
		justify-content: space-between;
		align-items: center;
		gap: 16px;
		font: inherit;
		color: var(--ink);
		text-decoration: none;
		text-align: left;
		background: none;
		border: 0;
		padding: 5px 12px;
		cursor: pointer;
	}
	.item:hover:not([aria-disabled='true']),
	.item:focus-visible {
		background: var(--leaf);
		outline: none;
	}
	.item[aria-disabled='true'] {
		color: var(--ink-faint);
		opacity: 0.6;
		cursor: default;
	}
	kbd {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
		border: 1px solid var(--rule);
		border-radius: 4px;
		padding: 0 5px;
	}
</style>
