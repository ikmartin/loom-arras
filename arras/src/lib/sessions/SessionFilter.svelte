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
	/* The mockup's pill: one rounded outline round two segments, the chosen one washed in the link's colour, the other in the leaf's. */
	.filter {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		white-space: nowrap;
	}
	.lbl {
		color: var(--ink-faint);
	}
	.choice {
		display: inline-flex;
		border: 1px solid var(--rule);
		border-radius: 10px;
		overflow: hidden;
	}
	.choice button {
		font: inherit;
		line-height: 1.5;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 0;
		padding: 1px 10px;
		cursor: pointer;
	}
	.choice button + button {
		border-left: 1px solid var(--rule);
	}
	.choice button:hover:not(:disabled):not(.on) {
		color: var(--ink);
		background: var(--sheet);
	}
	.choice button.on {
		background: var(--link-wash);
		color: var(--link);
	}
	.choice button:disabled {
		color: var(--ink-faint);
		cursor: not-allowed;
	}
</style>
