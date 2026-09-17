<script lang="ts">
	// The problems page (book 15.3.5): every diagnostic, grouped by code. The filters stand in the shell's left panel and live in the URL, so the home page's errors card opens it showing errors.
	import { page } from '$app/state';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { countBySeverity, groupDiagnostics } from '$lib/diagnostics';
	import { keyTarget } from '$lib/nav';
	import { setQuery } from '$lib/query';

	const m = $derived(store.manifest!);
	const SEVERITIES = ['error', 'warning', 'info'];
	const severity = $derived(SEVERITIES.includes(page.url.searchParams.get('severity') ?? '') ? page.url.searchParams.get('severity')! : '');
	const code = $derived(page.url.searchParams.get('code') ?? '');
	const pick = (v: string) => void setQuery(page.url, 'severity', severity === v ? '' : v);
	const groups = $derived(groupDiagnostics(m.diagnostics).filter((g) => (!severity || g.severity === severity) && (!code || g.code === code)));
	const counts = $derived(countBySeverity(m.diagnostics));
	const codes = $derived(groupDiagnostics(m.diagnostics).map((g) => g.code));
</script>

<main class="page">
	<h1>Problems <HelpDot label="what the problems page shows" topic="problems" /></h1>
	<p class="lead">Everything the publisher found wrong while building this corpus, worst first. An error is something a reader would notice; a warning is probably a mistake; information is a remark.</p>
	<p class="counts" data-testid="problem-counts">
		{#each [['error', counts.error ?? 0, 'errors'], ['warning', counts.warning ?? 0, 'warnings'], ['info', counts.info ?? 0, 'infos']] as [name, n, plural], i (name)}
			{#if i}<span class="sep">·</span>{/if}<button class="count" class:on={severity === name} aria-pressed={severity === name} onclick={() => pick(name as string)}>{n} {plural}</button>
		{/each}
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
							<span class="locs">{#each d.keys as k, j (k)}{#if j} → {/if}{@const href = keyTarget(m, k)}{#if href}<a {href}>{k}</a>{:else}<code>{k}</code>{/if}{/each}</span>
						{:else if g.affordance === 'filter'}
							<a href="/loose">loose nodes</a>
						{:else}
							<span class="locs">{#each d.locations as l, j (j)}<code>{l.file}:{l.line}</code>{/each}</span>
						{/if}
						{#if g.affordance !== 'cycle'}{#each d.keys as k (k)}{@const href = keyTarget(m, k)}{#if href}<a class="key" {href}>{k}</a>{:else}<code class="key">{k}</code>{/if}{/each}{/if}
					</li>
				{/each}
			</ul>
		</section>
	{:else}
		<p class="muted">{m.diagnostics.length ? 'Nothing matches.' : 'No diagnostics.'}</p>
	{/each}
</main>

<PagePanel label="Filters">
	<div class="filters">
		<label>severity<select value={severity} onchange={(e) => void setQuery(page.url, 'severity', e.currentTarget.value)} data-testid="filter-severity"><option value="">all</option><option value="error">error</option><option value="warning">warning</option><option value="info">info</option></select></label>
		<label>code<select value={code} onchange={(e) => void setQuery(page.url, 'code', e.currentTarget.value)}><option value="">all</option>{#each codes as c (c)}<option value={c}>{c}</option>{/each}</select></label>
		<p class="faint">{groups.reduce((n, g) => n + g.items.length, 0)} of {m.diagnostics.length} diagnostics</p>
	</div>
</PagePanel>

<style>
	.lead {
		max-width: var(--measure);
		color: var(--ink-soft);
		font-size: 12px;
		line-height: 1.6;
	}
	.counts {
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-soft);
	}
	.counts .sep {
		margin: 0 4px;
		color: var(--ink-faint);
	}
	.count {
		font: inherit;
		color: inherit;
		background: none;
		border: none;
		padding: 0 3px;
		border-radius: var(--rad-pill);
		cursor: pointer;
	}
	.count:hover {
		color: var(--link);
	}
	.count.on {
		background: var(--link-wash);
		color: var(--link);
	}
	.filters {
		display: grid;
		gap: var(--gap-tight);
	}
	.filters label {
		display: grid;
		gap: 2px;
		font-family: var(--sans);
		font-size: 9px;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
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
		color: var(--state-incomplete);
	}
	.sev-warning h2 code {
		color: var(--state-stale);
	}
</style>
