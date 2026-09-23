<script lang="ts">
	// A session read on its own (plan 0.13.3 E3): being audited. What happened in a sentence; what is still open, as a list to scan; what it touched; what settled; and the report, with the notation it declared beneath it. A section with nothing in it is left out, since a heading over nothing answers no question (C2's rule). Every date is relative, and the run log stays with the command line: which commands ran is the system's record, not a reader's question (P4).
	import type { Annotation } from '$lib/manifest/types';
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { ambiguous, notationOf, versionNote } from '$lib/review/run';
	import { pathFor, type Item } from '../item';
	import { follow, paneOfElement } from '../links';
	import { findings, itemAt, recordOf, said, targetName, touched } from './session';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const row = $derived((m.sessions ?? []).find((s) => s.id === item.id));
	const thread = $derived(recordOf(m, item.id));
	const all = $derived(findings(m, thread));
	const open = $derived(all.filter((a) => a.status === 'open'));
	const settled = $derived(all.filter((a) => a.status !== 'open'));
	const targets = $derived(touched(m, thread));
	const steps = $derived(thread.pipeline ?? []);
	const notation = $derived(notationOf(thread));
	const clashes = $derived(new Set(ambiguous(thread).map((d) => d.tex)));

	let report = $state<HTMLElement | null>(null);

	/** A finding's target, beside: the document at the finding's key when the session's document holds it, else its node (P5). */
	function open_(a: Annotation, from: HTMLElement): void {
		const at = itemAt(m, thread, a.target.key, a.target.page ?? undefined);
		if (at) follow(at, paneOfElement(from));
	}

	/** From the list to the finding's place in the report, which is the account the list indexes. */
	function inReport(id: string): void {
		report?.querySelector<HTMLElement>(`[data-annotation-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
	}

	/** The report's own finding marks open their target beside, as the list's rows do. */
	function wireReport(root: HTMLElement) {
		report = root.closest('.report') as HTMLElement | null;
		for (const el of root.querySelectorAll<HTMLElement>('[data-annotation-id]')) {
			if (el.dataset.wiredReport) continue;
			el.dataset.wiredReport = '1';
			el.setAttribute('role', 'button');
			el.setAttribute('tabindex', '0');
			const a = m.annotations[el.dataset.annotationId ?? ''];
			const go = () => a && open_(a, el);
			el.addEventListener('click', go);
			el.addEventListener('keydown', (e) => e.key === 'Enter' && go());
		}
	}

	const href = (key: string) => {
		const at = itemAt(m, thread, key);
		return at ? pathFor(m, at) : undefined;
	};
</script>

<div class="page item did" data-testid="session-did">
	<p class="what" data-testid="session-said">{said(m, thread, row)}</p>

	{#if open.length}
		<section data-testid="session-open">
			<h2>Still open</h2>
			<ul class="plain findings">
				{#each open as a (a.id)}
					<!-- `ann-<id>`: a mark's double-click in a document travels here, so the panes point at each other -->
					<li id="ann-{a.id}" data-testid="open-{a.id}">
						<button type="button" class="as-link finding" onclick={(e) => open_(a, e.currentTarget)}>
							{#if a.severity}<span class="sev sev-{a.severity}">{a.severity}</span>{/if}
							<span class="kind">{a.kind}</span>
							<span class="on" title={a.target.key}>{targetName(m, a.target.key)}</span>
						</button>
						{#if steps.length}<button type="button" class="as-link to-report" onclick={() => inReport(a.id)}>in the report</button>{/if}
						{#if versionNote(m, a)}<span class="moved">{versionNote(m, a)}</span>{/if}
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if targets.length}
		<section>
			<h2>What it touched</h2>
			<p class="targets">{#each targets as k (k)}<a class="chip" href={href(k)} title={k}>{targetName(m, k)}</a>{/each}</p>
		</section>
	{/if}

	{#if settled.length}
		<section data-testid="session-settled">
			<h2>What settled</h2>
			<ul class="plain findings">
				{#each settled as a (a.id)}
					<li id="ann-{a.id}"><span class="kind">{a.kind}</span> <span class="on" title={a.target.key}>{targetName(m, a.target.key)}</span></li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if steps.length}
		<section class="report">
			<h2>The report</h2>
			{#each steps as step (step.report)}
				<article class="step" data-testid="report-step">
					<p class="faint">{step.mode}{step.pass ? ` · pass ${step.pass}` : ''} · {targetName(m, step.target)}</p>
					{#if step.fragment}
						<Fragment path={step.fragment} standalone anchor="" onmounted={wireReport} />
					{:else}
						<p class="faint">This report was not rendered.</p>
					{/if}
				</article>
			{/each}
			{#if notation.length}
				<!-- The run's notation, never the corpus's, and a reference consulted while reading the report, so it stands beneath it, folded. -->
				<details class="notation" data-testid="notation">
					<summary>Notation ({notation.length}){#if clashes.size}<span class="clash-count"> · {clashes.size} with two meanings</span>{/if}</summary>
					<dl>
						{#each notation as d (d.tex)}
							<dt class:clash={clashes.has(d.tex)}><Tex text={'$' + d.tex + '$'} /></dt>
							<dd>
								{#each d.means as mean, i (i)}<p>{mean}</p>{/each}
								{#if clashes.has(d.tex)}<p class="clash-note">declared twice in this run with different meanings</p>{/if}
							</dd>
						{/each}
					</dl>
				</details>
			{/if}
		</section>
	{/if}
</div>

<style>
	.did {
		max-width: var(--measure);
		font-family: var(--sans);
		font-size: 12px;
	}
	.what {
		font-size: 14px;
		color: var(--ink);
		margin: 0 0 var(--gap-wide);
	}
	.findings li + li {
		margin-top: 4px;
	}
	.finding {
		display: inline-flex;
		gap: 6px;
		align-items: baseline;
	}
	.kind {
		font-weight: 500;
	}
	.on,
	.moved,
	.to-report {
		color: var(--ink-faint);
		margin-left: 6px;
	}
	.sev {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.sev-major {
		color: var(--state-incomplete);
	}
	.sev-moderate {
		color: var(--state-stale);
	}
	.targets {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.chip {
		font-size: 11px;
		padding: 1px 7px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		background: var(--leaf);
		color: var(--ink-soft);
	}
	.step + .step {
		margin-top: var(--gap-wide);
	}
	.report :global([data-annotation-id]) {
		cursor: pointer;
	}
	.report :global([data-annotation-id]:hover) {
		background: var(--link-wash);
	}
	.notation {
		margin-top: var(--gap);
	}
	.notation summary {
		cursor: pointer;
		color: var(--ink-soft);
	}
	.notation dl {
		display: grid;
		grid-template-columns: max-content minmax(0, 1fr);
		gap: 4px var(--gap);
	}
	.notation dd {
		margin: 0;
	}
	.notation dd p {
		margin: 0;
	}
	.clash,
	.clash-note,
	.clash-count {
		color: var(--state-incomplete);
	}
</style>
