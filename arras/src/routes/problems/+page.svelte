<script lang="ts">
	import { store } from '$lib/manifest/client.svelte';
	import { countBySeverity, groupDiagnostics } from '$lib/diagnostics';
	import { nodeUrl } from '$lib/nav';

	const m = $derived(store.manifest!);
	let severity = $state('');
	let code = $state('');
	const groups = $derived(groupDiagnostics(m.diagnostics).filter((g) => (!severity || g.severity === severity) && (!code || g.code === code)));
	const counts = $derived(countBySeverity(m.diagnostics));
	const codes = $derived(groupDiagnostics(m.diagnostics).map((g) => g.code));
</script>

<main class="page">
	<h1>Problems</h1>
	<p data-testid="problem-counts">{counts.error ?? 0} errors · {counts.warning ?? 0} warnings · {counts.info ?? 0} infos</p>
	<p>
		<label>severity <select bind:value={severity}><option value="">all</option><option value="error">error</option><option value="warning">warning</option><option value="info">info</option></select></label>
		<label>code <select bind:value={code}><option value="">all</option>{#each codes as c (c)}<option value={c}>{c}</option>{/each}</select></label>
	</p>
	{#each groups as g (g.code)}
		<section class="group sev-{g.severity}">
			<h2><code>{g.code}</code> <span class="muted">{g.severity} · {g.items.length}</span></h2>
			<ul>
				{#each g.items as d, i (i)}
					<li>
						{d.message}
						{#if g.affordance === 'both-locations' || g.affordance === 'paths'}
							<span class="locs">{#each d.locations as l, j (j)}<code>{l.file}:{l.line}</code>{/each}</span>
						{:else if g.affordance === 'cycle'}
							<span class="locs">{#each d.keys as k, j (k)}{#if j} → {/if}<a href={nodeUrl(k)}>{k}</a>{/each}</span>
						{:else if g.affordance === 'filter'}
							<a href="/loose">loose nodes</a>
						{:else}
							<span class="locs">{#each d.locations as l, j (j)}<code>{l.file}:{l.line}</code>{/each}</span>
						{/if}
						{#if g.affordance !== 'cycle'}{#each d.keys as k (k)}<a class="key" href={nodeUrl(k)}>{k}</a>{/each}{/if}
					</li>
				{/each}
			</ul>
		</section>
	{:else}
		<p class="muted">No diagnostics.</p>
	{/each}
</main>

<style>
	.group h2 {
		font-size: 1rem;
		margin-bottom: 0.2rem;
	}
	.locs code,
	.key {
		margin-left: 0.4rem;
		font-size: 0.85em;
	}
	.sev-error h2 code {
		color: var(--negative);
	}
	.sev-warning h2 code {
		color: var(--warning);
	}
</style>
