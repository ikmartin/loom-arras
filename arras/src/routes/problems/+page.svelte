<script lang="ts">
	// The problems page: every diagnostic, grouped by code, each group folded to its code and count until opened, so a long list is read code by code. The filters stand in the column and live in the URL, so a link can open it showing errors, or one code with its group open. Its bar is drawn at rest, since it is read by moving through it.
	import { page } from '$app/state';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import PagePanel from '$lib/shell/PagePanel.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { countBySeverity, groupBySubject, groupDiagnostics, subjectOf } from '$lib/diagnostics';
	import { copyText } from '$lib/clipboard';
	import { keyTarget } from '$lib/nav';
	import { setQuery } from '$lib/query';

	const m = $derived(store.manifest!);
	const SEVERITIES = ['error', 'warning', 'info'];
	const severity = $derived(SEVERITIES.includes(page.url.searchParams.get('severity') ?? '') ? page.url.searchParams.get('severity')! : '');
	const code = $derived(page.url.searchParams.get('code') ?? '');
	const subject = $derived(page.url.searchParams.get('subject') ?? '');
	const pick = (v: string) => void setQuery(page.url, 'severity', severity === v ? '' : v);
	const shown = $derived(
		m.diagnostics.filter(
			(d) => (!severity || d.severity === severity) && (!code || d.code === code) && (!subject || subjectOf(d) === subject)
		)
	);
	// Two kinds of thing go wrong, and they are not the same kind of work to put right: the source, and loom's own record of it.
	const bySubject = $derived(groupBySubject(shown).map((g) => ({ ...g, groups: groupDiagnostics(g.items) })));
	const subjects = $derived([...new Set(m.diagnostics.map(subjectOf))]);
	const counts = $derived(countBySeverity(m.diagnostics));
	const codes = $derived(groupDiagnostics(m.diagnostics).map((g) => g.code));

	// a group is folded to its code and count until opened; one code asked for by the URL stands open
	let opened = $state<Record<string, boolean>>({});
	const isOpen = (c: string) => opened[c] ?? c === code;
	const all = $derived(groupDiagnostics(shown).map((g) => g.code));
	const everyOpen = $derived(all.length > 0 && all.every(isOpen));
	function openAll(open: boolean): void {
		opened = Object.fromEntries(all.map((c) => [c, open]));
	}

	let copied = $state('');
	async function copy(command: string) {
		if (await copyText(command)) {
			copied = command;
			setTimeout(() => (copied = copied === command ? '' : copied), 1600);
		}
	}
</script>

<main class="page scrollbar-shown">
	<h1>Problems <HelpDot label="what the problems page shows" topic="problems" /></h1>
	<p class="lead">Everything the publisher found wrong while building this corpus, worst first. An error is something a reader would notice; a warning is probably a mistake; information is a remark.</p>
	<p class="counts" data-testid="problem-counts">
		{#each [['error', counts.error ?? 0, 'errors'], ['warning', counts.warning ?? 0, 'warnings'], ['info', counts.info ?? 0, 'infos']] as [name, n, plural], i (name)}
			{#if i}<span class="sep">·</span>{/if}<button class="count" class:on={severity === name} aria-pressed={severity === name} onclick={() => pick(name as string)}>{n} {plural}</button>
		{/each}
		{#if all.length}<span class="sep">·</span><button class="count" data-testid="problems-expand" onclick={() => openAll(!everyOpen)}>{everyOpen ? 'fold all' : 'expand all'}</button>{/if}
	</p>
	{#each bySubject as sub (sub.subject)}
	{#if subjects.length > 1}<h2 class="subject" data-testid="subject-heading">{sub.subject === 'record' ? 'The record' : 'The source'}</h2>{/if}
	{#each sub.groups as g (g.code)}
		<details class="group sev-{g.severity}" open={isOpen(g.code)} ontoggle={(e) => (opened[g.code] = e.currentTarget.open)} data-testid="problem-group">
			<summary><h2><code>{g.code}</code> <span class="muted">{g.severity} · {g.items.length}</span></h2></summary>
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
						{#if d.fixes?.length}
							<ul class="fixes">
								{#each d.fixes as f (f.command)}
									<li>
										<button type="button" data-testid="fix" onclick={() => copy(f.command)}>{copied === f.command ? 'copied' : 'copy'}</button>
										<code class="command">{f.command}</code>
										<span class="muted">{f.label}</span>
									</li>
								{/each}
							</ul>
						{/if}
					</li>
				{/each}
			</ul>
		</details>
	{/each}
	{:else}
		<p class="muted">{m.diagnostics.length ? 'Nothing matches.' : 'No diagnostics.'}</p>
	{/each}
</main>

<PagePanel label="Filters">
	<div class="filters">
		<label>severity<select value={severity} onchange={(e) => void setQuery(page.url, 'severity', e.currentTarget.value)} data-testid="filter-severity"><option value="">all</option><option value="error">error</option><option value="warning">warning</option><option value="info">info</option></select></label>
		<label>subject<select value={subject} onchange={(e) => void setQuery(page.url, 'subject', e.currentTarget.value)} data-testid="filter-subject"><option value="">all</option>{#each subjects as x (x)}<option value={x}>{x}</option>{/each}</select></label>
		<label>code<select value={code} onchange={(e) => void setQuery(page.url, 'code', e.currentTarget.value)}><option value="">all</option>{#each codes as c (c)}<option value={c}>{c}</option>{/each}</select></label>
		<p class="faint">{shown.length} of {m.diagnostics.length} diagnostics</p>
	</div>
</PagePanel>

<style>
	.subject {
		font-family: var(--sans);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--ink-faint);
		margin: var(--gap-wide) 0 0;
	}
	.fixes {
		list-style: none;
		margin: var(--gap-hair) 0 0;
		padding: 0;
	}
	.fixes li {
		font-size: 11px;
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
		margin-right: 4px;
		cursor: pointer;
	}
	.fixes button:hover {
		color: var(--link);
		border-color: var(--link);
	}
	.fixes .command {
		font-family: var(--mono);
	}
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
	.group summary {
		cursor: pointer;
		list-style-position: outside;
		margin-left: 1em;
	}
	.group h2 {
		display: inline;
		font-size: 1rem;
	}
	.group[open] summary {
		margin-bottom: 0.2rem;
	}
	.group {
		margin: 0 0 var(--gap-tight);
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
