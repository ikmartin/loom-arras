<script lang="ts">
	// A session read while working (plan 0.13.3 E2): the conversation beside its subject. The targets lead, as chips named as a reader names them, since a discussion on its own has no subject otherwise — the documents, a few results and a count of the rest; then one flow in time — the journal's messages, the findings marked by an edge in their kind's colour, what was attached, and the messages still landing — with a gutter of relative dates; the composer at the foot. No title: the tab names the session, once (P2).
	import type { Annotation, ThreadMessage } from '$lib/manifest/types';
	import { store } from '$lib/manifest/client.svelte';
	import { travel } from '$lib/travel/travel';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import Stream from '$lib/sessions/Stream.svelte';
	import Composer from '$lib/sessions/Composer.svelte';
	import { when } from '$lib/sessions/when';
	import { pathFor, type Item } from '../item';
	import { follow, paneOfElement } from '../links';
	import { itemAt, recordOf, targetName, touched } from './session';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const row = $derived((m.sessions ?? []).find((s) => s.id === item.id));
	const thread = $derived(recordOf(m, item.id));
	const targets = $derived(touched(m, thread));
	// The head says what the discussion is about without becoming its first screen: the documents it touched always, then the first few results, and the rest behind a count that unfolds in place.
	const SHOWN = 4;
	let allTargets = $state(false);
	const documents = $derived(targets.filter((k) => m.masters.some((x) => x.path === k)));
	const others = $derived(targets.filter((k) => !documents.includes(k)));
	const shownTargets = $derived([...documents, ...(allTargets ? others : others.slice(0, SHOWN))]);
	const folded = $derived(allTargets ? 0 : Math.max(0, others.length - SHOWN));

	type Entry = { at: string; message?: ThreadMessage; finding?: Annotation };
	/** The journal and the findings, in the order they happened. Replies stand under what they answer wherever it is read, so they are not entries of their own. */
	const flow = $derived<Entry[]>(
		[
			...thread.messages.map((message) => ({ at: message.time, message })),
			...Object.values(m.annotations)
				.filter((a) => a.run === item.id && !a.in_reply_to && !a.discarded)
				.map((finding) => ({ at: finding.created, finding }))
		].sort((a, b) => a.at.localeCompare(b.at))
	);

	/** The date beside an entry, said only where it changes: a gutter that repeats "today" forty times says nothing forty times. */
	const day = (i: number) => {
		const d = when(flow[i].at);
		return i && when(flow[i - 1].at) === d ? '' : d;
	};

	/** To the mark when a pane shows it; otherwise the finding's target opens beside, since a row that does nothing is a connection that cost the reader a click (P5). */
	function go(a: Annotation, from: HTMLElement): void {
		const mark = document.querySelector<HTMLElement>(`[data-pane] [data-annotation~=${JSON.stringify(a.id)}]`);
		if (mark) {
			travel(mark, from);
			return;
		}
		const at = itemAt(m, thread, a.target.key, a.target.page ?? undefined);
		if (at) follow(at, paneOfElement(from));
	}

	const href = (key: string) => {
		const at = itemAt(m, thread, key);
		return at ? pathFor(m, at) : undefined;
	};
</script>

<div class="stack" data-testid="discussion">
	<div class="body">
		{#if targets.length}
			<p class="targets" data-testid="session-targets">
				{#each shownTargets as k (k)}<a class="chip" href={href(k)} title={k}>{targetName(m, k)}</a>{/each}
				{#if folded}<button type="button" class="as-link more" data-testid="session-targets-more" onclick={() => (allTargets = true)}>and {folded} more</button>{/if}
			</p>
		{/if}
		<ol class="flow">
			{#each flow as e, i (e.finding?.id ?? `m${i}`)}
				<li class="entry" class:finding={!!e.finding} data-kind={e.finding?.kind}>
					<span class="when">{day(i)}</span>
					{#if e.finding}
						{@const a = e.finding}
						<div data-testid="beside-{a.id}">
							<button type="button" class="as-link kind" onclick={(ev) => go(a, ev.currentTarget)}>{a.kind}</button>
							<span class="on" title={a.target.key}>{targetName(m, a.target.key)}</span>
							{#if a.target.page}<span class="page" data-testid="beside-page-{a.id}">p.{a.target.page}{a.basis === 'box' ? ' (box)' : ''}</span>{/if}
							<span class="who">{a.author.label ?? a.author.id}</span>
							{#if a.status === 'resolved'}<span class="who">settled</span>{/if}
							{#if a.quote}<span class="quote">“<TexProse text={a.quote} />”</span>{/if}
							<Prose html={a.body_html} />
						</div>
					{:else if e.message}
						<div class="message">
							<span class="who">{e.message.author.label ?? e.message.author.id}</span>
							<Prose html={e.message.body_html} />
						</div>
					{/if}
				</li>
			{:else}
				<li class="entry"><span class="when"></span><p class="muted">Nothing has been said or written in this session yet.</p></li>
			{/each}
			{#if thread.attachments.length}
				<li class="entry">
					<span class="when"></span>
					<p class="attached" data-testid="attachments">
						attached {#each thread.attachments as at, i (i)}{#if i}, {/if}{at.name || at.kind}{at.count != null ? ` (${at.count})` : ''}{/each}
					</p>
				</li>
			{/if}
		</ol>
		<Stream session={item.id} />
	</div>
	<!-- docked at the foot, where a reply belongs; a run's record that is no session has nobody to write to (P3) -->
	{#if row}<Composer session={item.id} />{/if}
</div>

<style>
	.stack {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
		position: relative;
	}
	.body {
		flex: 1 1 auto;
		overflow: auto;
		padding: var(--gap) var(--gap-wide);
		font-family: var(--sans);
		font-size: 12px;
		max-width: calc(var(--measure) + 7rem);
	}
	.targets {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin: 0 0 var(--gap) 6rem;
	}
	.more {
		font-size: 11px;
		color: var(--ink-faint);
		align-self: center;
	}
	.chip {
		font-size: 11px;
		padding: 1px 7px;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		background: var(--leaf);
		color: var(--ink-soft);
	}
	.flow {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	/* The gutter: a fixed column for the date, so the text of every entry starts at one edge. */
	.entry {
		display: grid;
		grid-template-columns: 6rem minmax(0, 1fr);
		gap: 0;
	}
	.entry + .entry {
		margin-top: var(--gap-tight);
	}
	.when {
		color: var(--ink-faint);
		font-size: 11px;
		padding-top: 2px;
	}
	/* A finding is marked by an edge in its kind's colour, in the flow rather than in a section of its own (E2). */
	.entry.finding > div {
		border-left: 3px solid var(--rule-strong);
		padding-left: var(--gap-tight);
	}
	.entry[data-kind='objection'] > div {
		border-left-color: var(--state-incomplete);
	}
	.entry[data-kind='suggestion'] > div {
		border-left-color: var(--state-stale);
	}
	.entry[data-kind='question'] > div {
		border-left-color: var(--link);
	}
	.entry[data-kind='confirmation'] > div {
		border-left-color: var(--state-accepted);
	}
	.message {
		padding-left: calc(var(--gap-tight) + 3px);
	}
	.kind {
		font-weight: 500;
	}
	.who,
	.page,
	.on {
		color: var(--ink-faint);
		margin-left: 4px;
	}
	.quote {
		display: block;
		color: var(--ink-faint);
	}
	.attached {
		margin: 0;
		color: var(--ink-soft);
	}
</style>
