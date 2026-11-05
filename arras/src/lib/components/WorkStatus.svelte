<script lang="ts">
	// A work's status line on Info (plan 0.24.1): whether its paper and its LaTeX source are filed, how much of its digest exists and how much you have verified, and whether it has an overview. What is missing carries the action that makes it, where the publisher serves it: a missing paper is uploaded by the person or fetched, an overview is asked of an agent, and the rest is made by a library run, one run per work, which looks it up, fetches it, extracts its results and maps them, doing nothing that is done. The run's progress shows beneath while it goes, and stays until dismissed once this page has seen it run.
	import { onMount } from 'svelte';
	import type { Reference } from '$lib/manifest/types';
	import { resultCounts } from '$lib/library';
	import { jobs, running } from '$lib/jobs.svelte';
	import { can } from '$lib/write';
	import AddWork from './AddWork.svelte';
	import AskAgent from './AskAgent.svelte';
	import JobProgress from './JobProgress.svelte';
	import LibraryRun from './LibraryRun.svelte';
	import NetworkAsk from './NetworkAsk.svelte';

	let { citekey, ref }: { citekey: string; ref: Reference } = $props();

	let runs = $state(false);
	let uploads = $state(false);
	let uploading = $state(false);
	onMount(() => {
		void can('library-update').then((yes) => {
			runs = yes;
			if (yes) jobs.ask();
		});
		void can('library-file').then((yes) => (uploads = yes));
	});

	const paper = $derived(!!ref.artifacts?.pdf);
	const source = $derived(!!ref.artifacts?.source);
	const results = $derived(ref.digest?.nodes.length ?? 0);
	const verified = $derived(resultCounts(ref).verified);
	// the network can only help a work that lacks its paper or its source
	const network = $derived(!paper || !source);

	// a run this page saw going stays in view until dismissed; one that finished before it opened does not reappear
	let seen = $state<Record<string, boolean>>({});
	const job = $derived(jobs.forWork(citekey));
	$effect(() => {
		if (job && running(job) && !seen[job.id]) seen = { ...seen, [job.id]: true };
	});
	const shown = $derived(job && seen[job.id] ? job : undefined);
	// the network question stands under the whole line, not inside the part whose action asked it
	let answer = $state<((allow: boolean | null) => void) | null>(null);
	const ask = (go: (allow: boolean | null) => void) => (answer = go);
	function reply(allow: boolean | null): void {
		answer?.(allow);
		answer = null;
	}
</script>

<div class="status" data-testid="work-status">
	<span class="st" class:ok={paper} data-testid="status-paper">
		<span class="ic" aria-hidden="true">{paper ? '✓' : '–'}</span>Paper{#if paper}<span class="sub">filed</span>{/if}
		{#if uploads && !paper}<button class="act" onclick={() => (uploading = true)} data-testid="status-upload">Upload a PDF</button>{/if}
		{#if runs && !paper}<LibraryRun works={[citekey]} label="Fetch it" {network} test="run-get" onask={ask} />{/if}
	</span>
	<span class="st" class:ok={source} data-testid="status-source">
		<span class="ic" aria-hidden="true">{source ? '✓' : '–'}</span>Source{#if source}<span class="sub">LaTeX</span>{:else if paper}<span class="sub">none: results come from the pages</span>{/if}
	</span>
	<span class="st" class:ok={!!ref.digest} data-testid="status-digest">
		<span class="ic" aria-hidden="true">{ref.digest ? '✓' : '–'}</span>Digest{#if ref.digest}<span class="sub">{results} result{results === 1 ? '' : 's'} · {verified} verified</span>{/if}
		{#if runs && paper}<LibraryRun works={[citekey]} label={ref.digest ? 'Update' : 'Digest'} {network} test="run-digest" onask={ask} />{/if}
	</span>
	<span class="st" class:ok={!!ref.overview} data-testid="status-overview">
		<span class="ic" aria-hidden="true">{ref.overview ? '✓' : '–'}</span>Overview
		<AskAgent {citekey} {ref} quiet test="status-ask" />
	</span>
</div>
{#if uploads}<AddWork bind:open={uploading} work={citekey} />{/if}
{#if answer}<NetworkAsk onallow={() => reply(true)} onoffline={() => reply(false)} oncancel={() => reply(null)} />{/if}
{#if shown}
	<JobProgress
		job={shown}
		ondismiss={() => {
			const { [shown.id]: _, ...rest } = seen;
			seen = rest;
		}}
	/>
{/if}

<style>
	.act {
		border: 0;
		background: none;
		color: var(--link);
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
	.act:hover {
		text-decoration: underline;
	}
	.status {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin: 4px 0 16px;
		font-family: var(--sans);
	}
	.st {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		border: 1px solid var(--rule);
		background: var(--sheet);
		border-radius: 8px;
		padding: 4px 10px;
		font-size: 12px;
		color: var(--ink-soft);
	}
	.st.ok {
		color: var(--ink);
	}
	.ic {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 10px;
		font-weight: 700;
		background: var(--leaf);
		color: var(--ink-faint);
	}
	.st.ok .ic {
		background: var(--state-accepted-wash);
		color: var(--state-accepted);
	}
	.sub {
		color: var(--ink-faint);
	}
</style>
