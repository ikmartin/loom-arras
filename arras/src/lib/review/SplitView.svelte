<script lang="ts">
	// Reviewing a run (plan 0.11 Parts B and C): the document on the left, the run on the right, the two scrolling independently and pointing at each other.
	//
	// The panes are linked both ways and only both ways: clicking a finding scrolls the document to the sentence it is about, clicking a mark in the document scrolls the report to the finding that made it. That pairing is the whole reason this is one page rather than two.
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import type { CommentSlot } from '$lib/fragments/mount';
	import type { Annotation, Thread } from '$lib/manifest/types';
	import { anchorId, keyUrl, threadUrl } from '$lib/nav';
	import Tex from '$lib/math/Tex.svelte';
	import { ambiguous, documentOf, findingsOf, notationOf, runsOn, versionNote } from './run';

	let { thread }: { thread: Thread } = $props();

	const m = $derived(store.manifest!);
	const doc = $derived(documentOf(m, thread));
	const master = $derived(m.masters.find((x) => x.path === doc));
	const findings = $derived(findingsOf(m, thread));
	const others = $derived(runsOn(m, doc));
	const steps = $derived(thread.pipeline ?? []);
	const notation = $derived(notationOf(thread));
	const clashes = $derived(new Set(ambiguous(thread).map((d) => d.tex)));

	let tab = $state<'report' | 'journal'>('report');
	/** Which run the document's marks are showing. Empty means this one, so the pane follows the thread it was given rather than remembering the first it ever saw. */
	let picked = $state('');
	const shown = $derived(picked || thread.id);
	let leftEl = $state<HTMLElement | null>(null);
	let rightEl = $state<HTMLElement | null>(null);
	let selected = $state('');

	// Every annotation on this document is marked in the fragment by the publisher, whichever run made it. Dimming the
	// ones outside the run being read is what lets the picker change what you are looking at without reloading anything.
	$effect(() => {
		const root = leftEl;
		const run = shown;
		if (!root) return;
		for (const mark of root.querySelectorAll<HTMLElement>('[data-annotation]')) {
			const ids = (mark.dataset.annotation ?? '').split(/\s+/).filter(Boolean);
			const mine = ids.some((i) => m.annotations[i]?.run === run);
			mark.classList.toggle('other-run', !mine);
		}
	});

	function slots(key: string): CommentSlot[] {
		return Object.values(m.annotations)
			.filter((a) => !a.discarded && !a.in_reply_to && a.target.key === key)
			.map((a) => ({ id: a.id, where: 'count' }));
	}

	/** From a finding to the sentence it is about. */
	function showInDocument(a: Annotation) {
		selected = a.id;
		const mark = leftEl?.querySelector<HTMLElement>(`[data-annotation~="${a.id}"]`);
		const fallback = leftEl?.querySelector<HTMLElement>(`#${CSS.escape(anchorId(a.target.key))}`);
		(mark ?? fallback)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
	}

	/** From a mark to the finding that made it. */
	function showInReport(id: string) {
		selected = id;
		tab = 'report';
		queueMicrotask(() => {
			rightEl?.querySelector<HTMLElement>(`#finding-${CSS.escape(id)}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		});
	}

	function wireLeft(root: HTMLElement) {
		leftEl = root;
		for (const mark of root.querySelectorAll<HTMLElement>('[data-annotation]')) {
			if (mark.dataset.wiredSplit) continue;
			mark.dataset.wiredSplit = '1';
			mark.addEventListener('click', () => {
				const ids = (mark.dataset.annotation ?? '').split(/\s+/).filter(Boolean);
				if (ids[0]) showInReport(ids[0]);
			});
		}
	}

	function wireReport(root: HTMLElement) {
		rightEl = root;
		for (const el of root.querySelectorAll<HTMLElement>('[data-annotation-id]')) {
			if (el.dataset.wiredSplit) continue;
			el.dataset.wiredSplit = '1';
			el.setAttribute('role', 'button');
			el.setAttribute('tabindex', '0');
			const a = m.annotations[el.dataset.annotationId ?? ''];
			const go = () => a && showInDocument(a);
			el.addEventListener('click', go);
			el.addEventListener('keydown', (e) => e.key === 'Enter' && go());
		}
	}
</script>

<div class="split" data-testid="split-view">
	<section class="pane left" aria-label="the document">
		{#if master}
			<p class="faint"><code>{master.path}</code></p>
			<Fragment path={master.fragment} master={master.path} comments={slots} onmounted={wireLeft} />
		{:else if thread.targets.length}
			<p class="faint">No document holds what this run looked at.</p>
			<ul class="plain">
				{#each thread.targets as k (k)}<li><a href={keyUrl(m, k)}>{k}</a></li>{/each}
			</ul>
		{:else}
			<p class="faint">This run annotated nothing.</p>
		{/if}
	</section>

	<section class="pane right" aria-label="the run">
		<nav class="tabs">
			<button class:on={tab === 'report'} onclick={() => (tab = 'report')} data-testid="tab-report">Report</button>
			<button class:on={tab === 'journal'} onclick={() => (tab = 'journal')} data-testid="tab-journal">Journal</button>
			{#if others.length > 1}
				<label class="picker">
					run
					<select value={shown} onchange={(e) => (picked = e.currentTarget.value)} data-testid="run-picker">
						{#each others as t (t.id)}<option value={t.id}>{t.title}</option>{/each}
					</select>
				</label>
			{/if}
		</nav>

		{#if shown !== thread.id}
			<p class="faint">Showing <a href={threadUrl(shown)}>{m.threads[shown]?.title ?? shown}</a>'s marks in the document; the report below is still this run's.</p>
		{/if}

		{#if tab === 'report'}
			{#if notation.length}
				<!-- Notation is the run's, never the corpus's: a symbol an agent introduced to explain something is not a symbol the paper uses. Collapsed, because it is a reference you consult rather than prose you read. -->
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
			{#if findings.document.length}
				<!-- First and in a section of its own: these are about the thing the left pane is showing as a whole, where every other finding is about one node inside it. -->
				<section class="doc-findings" data-testid="document-findings">
					<h2>About the document</h2>
					<ul class="plain">
						{#each findings.document as a (a.id)}
							<li class:sel={selected === a.id}>
								<button class="finding" onclick={() => showInDocument(a)}>
									{#if a.severity}<span class="sev sev-{a.severity}">{a.severity}</span>{/if}
									<span class="kind">{a.kind}</span>
								</button>
								<div class="body">{@html a.body_html}</div>
								{#if versionNote(m, a)}<p class="moved">{versionNote(m, a)}</p>{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			{#each steps as step (step.report)}
				<article class="step" data-testid="report-step">
					<p class="faint">{step.mode}{step.pass ? ` · pass ${step.pass}` : ''} · {step.target}</p>
					{#if step.fragment}
						<Fragment path={step.fragment} standalone onmounted={wireReport} />
					{:else}
						<p class="faint">This report was not rendered.</p>
					{/if}
				</article>
			{:else}
				<p class="faint">This run wrote no report.</p>
			{/each}
		{:else}
			<div class="messages" data-testid="journal">
				{#each thread.messages as msg, i (i)}
					<article class="message">
						<p class="faint">{msg.author.id} · {msg.time}</p>
						<div>{@html msg.body_html}</div>
					</article>
				{:else}
					<p class="faint">This run kept no journal.</p>
				{/each}
			</div>
		{/if}
	</section>
</div>

<style>
	.split {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--gap-wide);
		align-items: start;
	}
	.pane {
		min-width: 0;
		max-height: calc(100vh - 6rem);
		overflow-y: auto;
	}
	.pane.right {
		border-left: 1px solid var(--rule);
		padding-left: var(--gap-wide);
	}
	.tabs {
		display: flex;
		gap: var(--gap-tight);
		align-items: baseline;
		border-bottom: 1px solid var(--rule);
		margin-bottom: var(--gap);
		position: sticky;
		top: 0;
		background: var(--paper);
	}
	.tabs button {
		background: none;
		border: 0;
		border-bottom: 2px solid transparent;
		padding: 0.3em 0.2em;
		font: inherit;
		color: var(--ink-soft);
		cursor: pointer;
	}
	.tabs button.on {
		color: var(--ink);
		border-bottom-color: var(--ink);
	}
	.picker {
		margin-left: auto;
		font-size: 0.85em;
		color: var(--ink-soft);
	}
	.notation {
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		padding: var(--gap-tight) var(--gap);
		margin-bottom: var(--gap-wide);
		font-size: 0.9em;
	}
	.notation summary {
		cursor: pointer;
		color: var(--ink-soft);
		font-family: var(--sans);
		font-size: 0.8em;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.notation dl {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 0.3em var(--gap);
		margin: var(--gap-tight) 0 0;
	}
	.notation dt.clash {
		color: var(--state-incomplete, var(--ink));
	}
	.notation dd {
		margin: 0;
	}
	.notation dd p {
		margin: 0;
	}
	.clash-note,
	.clash-count {
		color: var(--state-incomplete, var(--ink-faint));
		font-size: 0.85em;
	}
	.doc-findings {
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		padding: var(--gap);
		margin-bottom: var(--gap-wide);
		background: var(--sheet);
	}
	.doc-findings h2 {
		font-size: 0.8em;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-tight);
	}
	.doc-findings li + li {
		margin-top: var(--gap);
	}
	.doc-findings li.sel {
		outline: 2px solid var(--link);
		outline-offset: 3px;
	}
	.finding {
		background: none;
		border: 0;
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
	.sev {
		font-size: 0.68em;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		padding: 0 0.3em;
		border: 1px solid var(--rule-strong);
		border-radius: 2px;
	}
	.moved {
		font-size: 0.8em;
		color: var(--state-stale, var(--ink-faint));
		margin: 0.2em 0 0;
	}
	.step + .step {
		margin-top: var(--gap-wide);
		border-top: 1px solid var(--rule);
		padding-top: var(--gap);
	}
	.message {
		border-left: 3px solid var(--rule);
		padding-left: 0.75rem;
		margin: 1rem 0;
	}
	/* A mark another run made stays legible but stops competing: the picker changed what you are reading, not what exists. */
	.pane.left :global(.other-run) {
		opacity: 0.35;
	}
	.pane.right :global([data-annotation-id]) {
		cursor: pointer;
	}
	.pane.right :global([data-annotation-id]:hover) {
		background: var(--link-wash);
	}
	@media (max-width: 60rem) {
		.split {
			grid-template-columns: minmax(0, 1fr);
		}
		.pane {
			max-height: none;
		}
		.pane.right {
			border-left: 0;
			padding-left: 0;
			border-top: 1px solid var(--rule);
			padding-top: var(--gap);
		}
	}
</style>
