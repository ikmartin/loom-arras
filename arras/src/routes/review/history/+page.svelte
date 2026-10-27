<script lang="ts">
	// Review › History: every step the history recorded, newest first — what it was, when, who, the document it concerned — with each landmark linked, and flagged when no live draft leads to it, since then this is the one place it is reached from.
	import { store } from '$lib/manifest/client.svelte';
	import { canonUrl, masterUrl } from '$lib/nav';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';

	const m = $derived(store.manifest!);
	const steps = $derived([...(m.history?.steps ?? [])].reverse());
	const live = $derived(new Set(m.masters.map((x) => x.path)));
	const ACTION: Record<string, string> = { import: 'imported', stamp: 'stamped', copy: 'agent document', adopt: 'adopted' };
	const file = (path: string) => path.split('/').pop() || path;
</script>

<main class="page">
	<ReviewHeading title="History" />
	{#if !steps.length}
		<p class="muted">Nothing has been recorded yet.</p>
	{:else}
		<table class="list" data-testid="history-table">
			<thead><tr><th>Step</th><th>What</th><th>Document</th><th>Landmark</th><th>When</th><th>Who</th></tr></thead>
			<tbody>
				{#each steps as s (s.step)}
					<tr data-testid="history-step-{s.step}">
						<td class="num">{String(s.step).padStart(4, '0')}</td>
						<td>{ACTION[s.action] ?? s.action}{#if s.message}<div class="muted">{s.message}</div>{/if}</td>
						<td>{#if s.in && live.has(s.in)}<a href={masterUrl(s.in)}>{file(s.in)}</a>{:else if s.document}<span class="muted">{file(s.document)}</span>{:else}<span class="muted">the whole quilt</span>{/if}</td>
						<td>
							{#if s.landmark}
								<a href={canonUrl(s.landmark)}>{s.name}</a>
								{#if !s.in}<span class="orphan" title="no live draft leads to this landmark" data-testid="history-orphan-{s.step}">no draft leads here</span>{/if}
							{/if}
						</td>
						<td>{s.when.slice(0, 10)}</td>
						<td>{s.actor ?? ''}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</main>

<style>
	.num {
		font-variant-numeric: tabular-nums;
		color: var(--ink-soft);
	}
	.orphan {
		margin-left: 6px;
		font-size: 11px;
		color: var(--state-stale);
	}
</style>
