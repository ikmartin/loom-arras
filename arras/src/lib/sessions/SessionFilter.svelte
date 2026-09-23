<script lang="ts">
	// Which sessions' annotations the page draws (plan 0.13.3 F3). It governs what is drawn on a document, not which sessions are listed, so it stands above the content rather than in the session picker; writes still land in the selected session whatever it shows.
	import { store } from '$lib/manifest/client.svelte';
	import { selected, sessionView } from './sessions.svelte';

	const here = $derived(selected(store.manifest));

	function view(v: 'current' | 'all'): void {
		sessionView.view = v;
		sessionView.save();
	}
</script>

<span class="filter">
	<span class="lbl">showing annotations from</span>
	<span class="choice" role="group" aria-label="which annotations the page shows">
		<button
			type="button"
			class:on={sessionView.view === 'current'}
			aria-pressed={sessionView.view === 'current'}
			disabled={!here}
			title={here ? `only ${here.title}` : 'Nothing is selected yet'}
			data-testid="show-current"
			onclick={() => view('current')}>this session</button
		><button type="button" class:on={sessionView.view === 'all'} aria-pressed={sessionView.view === 'all'} data-testid="show-all" onclick={() => view('all')}>all</button>
	</span>
</span>

<style>
	.filter {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		white-space: nowrap;
	}
	.lbl {
		color: var(--ink-faint);
	}
	/* One segmented control: the two values of a single setting share a border (15.7). */
	.choice {
		display: inline-flex;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		overflow: hidden;
	}
	.choice button {
		font: inherit;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 0;
		padding: 1px 8px;
		cursor: pointer;
	}
	.choice button + button {
		border-left: 1px solid var(--rule);
	}
	.choice button.on {
		background: var(--link-wash);
		color: var(--link);
	}
	.choice button:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}
</style>
