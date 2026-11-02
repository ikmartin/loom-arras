<script lang="ts">
	// Where agents may not write, a draft until Save; what is always protected; and the apps that start loom here. A saved list the permission file Claude Code reads has not caught up with is said at the top, with the act that rewrites it.
	import { store } from '$lib/manifest/client.svelte';
	import type { QuiltSettings } from '$lib/manifest/types';
	import { write } from '$lib/write';
	import { draft } from './draft.svelte';
	import Chips from './Chips.svelte';
	import Row from './Row.svelte';

	let { config, editable, canUpdate }: { config: QuiltSettings; editable: boolean; canUpdate: boolean } = $props();
	const deny = $derived((draft.value('agents.deny') as string[] | undefined) ?? []);
	const agents = $derived(config.agents);
	const stale = $derived(`Claude Code's permission file is behind this list, so Claude Code holds agents to an older boundary; loom already refuses them by this one.${'agents.deny' in draft.changes ? ' Save the list first.' : ''}`);
	let pattern = $state('');
	let busy = $state(false);
	let error = $state('');

	function add(): void {
		const p = pattern.trim();
		if (!p) return;
		if (!deny.includes(p)) draft.set('agents.deny', [...deny, p]);
		pattern = '';
	}

	async function update(): Promise<void> {
		busy = true;
		error = '';
		const answer = await write('agents-update', {});
		if (answer.ok) await store.refresh();
		else error = answer.error?.message ?? 'Could not rewrite the permission files';
		busy = false;
	}
</script>

{#if agents.stale}
	<div class="note warn" data-testid="agents-stale">
		<span>{stale}</span>
		{#if canUpdate}<button class="btn" disabled={busy || 'agents.deny' in draft.changes} onclick={update} data-testid="agents-update">{busy ? 'Updating…' : 'Update Claude Code'}</button>{/if}
	</div>
{/if}
{#if error}<p class="note warn" role="alert">{error}</p>{/if}
{#if !agents.layer}
	<div class="note info" data-testid="agents-no-layer">This quilt has no agent layer, so no agent is told what loom is. To write one, run <code>{agents.command}</code> in a terminal.</div>
{/if}
<div class="card">
	<Row id="agents.deny" stack refused={draft.refused['agents.deny']}>
		<Chips test="config-agents.deny" items={deny} remove={editable ? (p) => draft.set('agents.deny', deny.filter((x) => x !== p)) : undefined} />
		{#if editable}
			<form
				class="add"
				onsubmit={(e) => {
					e.preventDefault();
					add();
				}}
			>
				<input class="text mono" bind:value={pattern} placeholder="paper/  or  *.bib" aria-label="A path agents may not write" data-testid="deny-pattern" />
				<button class="btn" type="submit" disabled={!pattern.trim()} data-testid="deny-add">Add</button>
			</form>
		{:else if !deny.length}
			<p class="aside">Nothing beyond what is always protected.</p>
		{/if}
	</Row>
	<Row id="agents.protected" stack>
		<Chips test="agents-protected" fixed items={agents.protected} />
	</Row>
</div>
{#if agents.layer}
	<div class="card">
		<Row id="agents.apps" stack>
			<ul class="apps" data-testid="agents-apps">
				{#each agents.clients as c (c.key)}
					<li>
						<span class="app">{c.label}</span>
						<span class="file">{c.file}</span>
						{#if c.set_up}<span class="ok">Set up</span>{:else}<code class="how" title="Run in a terminal to set it up">{c.command}</code>{/if}
					</li>
				{/each}
			</ul>
			{#if agents.variant === 'shell'}<p class="aside">Agents here run loom in a shell, so no app starts loom's server.</p>{/if}
		</Row>
	</div>
{/if}

<style>
	.apps {
		list-style: none;
		margin: 10px 0 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.apps li {
		display: grid;
		grid-template-columns: 8rem minmax(0, 1fr) auto;
		gap: 10px;
		align-items: baseline;
		font-size: 13px;
	}
	.app {
		color: var(--ink);
	}
	.file {
		font-family: var(--mono);
		font-size: 11.5px;
		color: var(--ink-faint);
		overflow-wrap: anywhere;
	}
	.ok {
		color: var(--state-accepted);
		font-size: 12.5px;
	}
	.how {
		font-family: var(--mono);
		font-size: 11.5px;
		color: var(--ink-soft);
		background: var(--leaf);
		padding: 1px 6px;
		border-radius: 4px;
	}
	@media (max-width: 560px) {
		.apps li {
			grid-template-columns: minmax(0, 1fr);
			gap: 2px;
		}
	}
</style>
