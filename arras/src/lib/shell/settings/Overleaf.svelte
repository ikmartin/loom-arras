<script lang="ts">
	// The Git workspace the quilt is paired with, such as an Overleaf project: shown, never paired from here, since pairing takes a folder on this computer and a terminal of the person's own.
	import type { QuiltSettings } from '$lib/manifest/types';
	import Row from './Row.svelte';

	let { config }: { config: QuiltSettings } = $props();
	const sync = $derived(config.sync);
</script>

{#if sync.paired}
	<div class="note ok" data-testid="sync-paired">Paired{sync.workspace ? ` with ${sync.workspace}` : ''}.</div>
	<div class="card">
		<Row id="sync" stack>
			<dl>
				<dt>Folder</dt><dd class="mono">{sync.directory}</dd>
				{#if sync.branch}<dt>Branch</dt><dd class="mono">{sync.branch}</dd>{/if}
				<dt>Documents</dt><dd class="mono">{sync.documents.join(', ')}</dd>
			</dl>
		</Row>
	</div>
{:else}
	<div class="note info" data-testid="sync-unpaired">Not paired. Clone the project's Git address anywhere, then pair the quilt with that folder in a terminal: <code>{sync.command}</code></div>
{/if}

<style>
	dl {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 6px 14px;
		margin: 10px 0 0;
		font-size: 13px;
	}
	dt {
		color: var(--ink-faint);
	}
	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
	.mono {
		font-family: var(--mono);
		font-size: 12.5px;
	}
</style>
