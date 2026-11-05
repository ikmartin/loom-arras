<script lang="ts">
	// One library run as it goes: each step with a tick, a spinner or a dot, how far through the works it is and the one it is on, or through a book's pages; a run that only reads a text speaks of that rather than of digests. Then the run's verdict, with what it said folded beneath, or why it failed.
	import { readingOnly, type Job } from '$lib/jobs.svelte';

	let { job, ondismiss }: { job: Job; ondismiss?: () => void } = $props();

	const LABEL: Record<string, string> = {
		gather: 'Gather the bibliography',
		resolve: 'Look up identifiers',
		fetch: 'Fetch papers and sources',
		extract: 'Extract results',
		map: 'Read the text'
	};
	const reading = $derived(readingOnly(job));
	const noText = $derived(reading && !!job.report?.works?.some((w) => w.no_text));
	const heading = $derived(
		job.state === 'queued'
			? 'Waiting for the run before it'
			: job.state === 'running'
				? reading
					? 'Reading its text'
					: 'Running in loom'
				: job.state === 'failed'
					? 'The run failed'
					: noText
						? 'It has no text to read: it opens as usual, but nothing can search or quote its pages'
						: (job.report?.verdict ?? 'Done')
	);
	const said = $derived((job.report?.groups ?? []).filter((g) => g.items.length));
</script>

<div class="run" class:failed={job.state === 'failed'} data-testid="job-progress" data-state={job.state}>
	<p class="head">
		<strong>{heading}</strong>
		{#if job.state === 'running' || job.state === 'queued'}<span class="aside">· keeps going if you leave this page</span>{/if}
		{#if job.online}<span class="aside">· with the network</span>{/if}
		{#if ondismiss && (job.state === 'done' || job.state === 'failed')}<button class="close" aria-label="Dismiss" onclick={ondismiss}>×</button>{/if}
	</p>
	<ol>
		{#each job.steps as step (step.name)}
			<li class={step.state} data-testid="job-step" data-step={step.name} data-state={step.state}>
				<span class="mark" aria-hidden="true">{#if step.state === 'done'}✓{:else if step.state === 'running'}<span class="spin"></span>{:else if step.state === 'skipped'}–{:else}·{/if}</span>
				<span>{LABEL[step.name] ?? step.name}</span>
				{#if step.state === 'running' && step.total}<span class="aside" data-testid="job-step-progress">{#if step.item === 'pages'}{Math.round((step.n / step.total) * 100)}% done{:else}{step.n} of {step.total}{#if step.item} · {step.item}{/if}{/if}</span>{/if}
				{#if step.state === 'skipped'}<span class="aside">nothing to do here</span>{/if}
			</li>
		{/each}
	</ol>
	{#if job.state === 'failed'}<p class="error" role="alert">{job.error}</p>{/if}
	{#if said.length && !noText}
		<details>
			<summary>What the run said</summary>
			{#each said as g (g.heading)}
				<p class="group">{g.heading}</p>
				<ul>
					{#each g.items as item, i (i)}<li>{#if item.key}<code>{item.key}</code> {/if}{item.text}{#each item.fixes ?? [] as fix (fix)} <code class="fix">{fix}</code>{/each}</li>{/each}
				</ul>
			{/each}
		</details>
	{/if}
</div>

<style>
	.run {
		border: 1px solid var(--rule);
		border-radius: 10px;
		background: var(--sheet);
		padding: 10px 14px;
		margin: 0 0 16px;
		font-family: var(--sans);
		font-size: 12.5px;
	}
	.run.failed {
		border-color: var(--state-conflicted);
	}
	.head {
		display: flex;
		align-items: baseline;
		gap: 6px;
		margin: 0;
	}
	.close {
		margin-left: auto;
		border: 0;
		background: none;
		color: var(--ink-faint);
		font-size: 16px;
		line-height: 1;
		cursor: pointer;
	}
	ol {
		list-style: none;
		margin: 6px 0 0;
		padding: 0;
	}
	li {
		display: flex;
		gap: 8px;
		align-items: center;
		padding: 2px 0;
		color: var(--ink-faint);
	}
	li.done,
	li.running {
		color: var(--ink);
	}
	li.running {
		font-weight: 500;
	}
	.mark {
		width: 14px;
		text-align: center;
	}
	li.done .mark {
		color: var(--state-accepted);
	}
	.aside {
		color: var(--ink-faint);
		font-weight: 400;
	}
	.spin {
		display: inline-block;
		width: 10px;
		height: 10px;
		border: 2px solid var(--rule);
		border-top-color: var(--link);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	.error {
		color: var(--state-conflicted);
		margin: 6px 0 0;
	}
	details {
		margin-top: 6px;
	}
	summary {
		cursor: pointer;
		color: var(--ink-soft);
	}
	.group {
		margin: 6px 0 2px;
		font-weight: 500;
	}
	ul {
		margin: 0;
		padding-left: 18px;
	}
	code {
		font-family: var(--mono);
		font-size: 0.92em;
	}
	.fix {
		color: var(--ink-soft);
	}
</style>
