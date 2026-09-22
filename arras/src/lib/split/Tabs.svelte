<script lang="ts">
	// Tabs, and **only in the content pane** (plan 0.13 §7).
	//
	// The rule is the point of the component. A discussion is one stream in time; tabs across it would hide half of
	// what was said behind a control, and the half hidden is the half a reader does not know to look for. The content
	// pane is different: a document and the journal written against it are two texts, and only one can be read at once.
	let {
		tabs,
		value = $bindable('')
	}: { tabs: { id: string; label: string }[]; value?: string } = $props();
</script>

<div class="tabs" role="tablist" aria-label="what the content pane is showing">
	{#each tabs as t (t.id)}
		<button
			type="button"
			role="tab"
			class:on={value === t.id}
			aria-selected={value === t.id}
			data-testid="tab-{t.id}"
			onclick={() => (value = t.id)}>{t.label}</button
		>
	{/each}
</div>

<style>
	.tabs {
		display: flex;
		gap: var(--gap-tight);
		align-items: baseline;
		border-bottom: 1px solid var(--rule);
		margin-bottom: var(--gap);
		position: sticky;
		top: 0;
		background: var(--paper);
		z-index: 2;
	}
	button {
		background: none;
		border: 0;
		border-bottom: 2px solid transparent;
		padding: 0.3em 0.2em;
		font: inherit;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
		cursor: pointer;
	}
	button.on {
		color: var(--ink);
		border-bottom-color: var(--ink);
	}
</style>
