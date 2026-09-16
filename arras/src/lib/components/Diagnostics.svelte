<script lang="ts">
	import type { Diagnostic } from '$lib/manifest/types';
	import { keyTarget } from '$lib/nav';
	import { store } from '$lib/manifest/client.svelte';

	let { items }: { items: Diagnostic[] } = $props();
</script>

{#if items.length}
	<ul class="diagnostics">
		{#each items as d, i (i)}
			<li class="sev-{d.severity}">
				<span class="sev">{d.severity}</span>
				<code>{d.code}</code>
				{d.message}
				{#each d.locations as loc, j (j)}
					<span class="loc">{loc.file}:{loc.line}</span>
				{/each}
				{#each d.keys as k (k)}
					{@const href = keyTarget(store.manifest, k)}
					{#if href}<a {href}>{k}</a>{:else}<code class="unlinked">{k}</code>{/if}
				{/each}
			</li>
		{/each}
	</ul>
{:else}
	<p class="faint">None.</p>
{/if}

<style>
	.diagnostics {
		list-style: none;
		padding: 0;
	}
	.diagnostics li {
		font-size: 11px;
		line-height: 1.5;
		padding: var(--gap-hair) 0;
		border-bottom: 1px solid var(--rule);
	}
	.sev {
		display: inline-block;
		width: 4.5rem;
		font-family: var(--sans);
		font-size: 9px;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	.sev-error .sev {
		color: var(--state-incomplete);
	}
	.sev-warning .sev {
		color: var(--state-stale);
	}
	.loc,
	code {
		font-family: var(--mono);
		font-size: 0.85em;
		margin-left: 0.4rem;
	}
	a,
	.unlinked {
		margin-left: 0.4rem;
	}
	.unlinked {
		color: var(--ink-faint);
	}
</style>
