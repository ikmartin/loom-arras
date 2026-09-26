<script lang="ts">
	// The frame's one rail (plan 0.16, decision 6). It holds only what concerns both panes: the annotation filter at its left, which governs what every document draws, and **compare** at its right, which acts on the two documents on screen. Nothing about one item stands here: an item's views are at the end of its pane's tab strip, and its controls on the focused pane.
	//
	// **Compare is drawn disabled** until it is built (plan 0.17), its title saying what it will do and when: a control that did nothing when pressed would claim what is not so (P3).
	import SessionFilter from '$lib/sessions/SessionFilter.svelte';
	import Icon from '$lib/components/Icon.svelte';
</script>

<div class="global-rail" data-testid="reading-rail">
	<SessionFilter />
	<button type="button" class="compare" disabled aria-disabled="true" title="Compare the two open documents — arrives in 0.17" data-testid="rail-compare"
		><Icon name="compare" size={14} />compare<small aria-hidden="true">0.17</small></button
	>
</div>

<style>
	/* One line, 12.5px: the filter a quiet label and a pill at the left, compare at the right. */
	.global-rail {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		height: var(--reading-rail);
		padding: 0 12px;
		border-bottom: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink-soft);
		white-space: nowrap;
		overflow: hidden;
	}
	.compare {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font: inherit;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 0;
		cursor: default;
	}
	.compare small {
		font-size: 9px;
		letter-spacing: 0.04em;
		margin-left: 2px;
	}
</style>
