<script lang="ts">
	import type { Diagnostic } from '$lib/manifest/types';
	import { keyTarget } from '$lib/nav';
	import { store } from '$lib/manifest/client.svelte';
	import { copyText } from '$lib/clipboard';

	let { items }: { items: Diagnostic[] } = $props();

	// A fix is a command to copy and run; nothing here runs anything, and the command stays on screen so it can be read or copied by hand when the clipboard is refused.
	let copied = $state('');
	async function copy(command: string) {
		const ok = await copyText(command);
		copied = ok ? command : '';
		if (ok) setTimeout(() => (copied = copied === command ? '' : copied), 1600);
	}
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
				{#if d.fixes?.length}
					<ul class="fixes">
						{#each d.fixes as f (f.command)}
							<li>
								<button type="button" data-testid="fix" onclick={() => copy(f.command)} title="copy this command">
									{copied === f.command ? 'copied' : 'copy'}
								</button>
								<code class="command">{f.command}</code>
								<span class="faint">{f.label}</span>
							</li>
						{/each}
					</ul>
				{/if}
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
	.fixes {
		list-style: none;
		margin: var(--gap-hair) 0 0 4.5rem;
		padding: 0;
	}
	.fixes li {
		border: 0;
		padding: 1px 0;
	}
	.fixes button {
		font-family: var(--sans);
		font-size: 9px;
		text-transform: uppercase;
		color: var(--ink-faint);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 0 4px;
		cursor: pointer;
	}
	.fixes button:hover {
		color: var(--link);
		border-color: var(--link);
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
