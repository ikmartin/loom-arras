<script lang="ts">
	import type { Diagnostic } from '$lib/manifest/types';
	import { nodeUrl } from '$lib/nav';

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
					<a href={nodeUrl(k)}>{k}</a>
				{/each}
			</li>
		{/each}
	</ul>
{:else}
	<p class="muted">None.</p>
{/if}

<style>
	.diagnostics {
		list-style: none;
		padding: 0;
	}
	.diagnostics li {
		padding: 0.25rem 0;
		border-bottom: 1px solid var(--rule);
	}
	.sev {
		display: inline-block;
		width: 4.5rem;
		font-size: 0.75rem;
		text-transform: uppercase;
		color: var(--muted);
	}
	.sev-error .sev {
		color: var(--negative);
	}
	.sev-warning .sev {
		color: var(--warning);
	}
	.loc,
	code {
		font-family: var(--mono);
		font-size: 0.85em;
		margin-left: 0.4rem;
	}
	a {
		margin-left: 0.4rem;
	}
</style>
