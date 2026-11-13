<script lang="ts">
	// Review › Your Changes: the mathematics first, then what waits to be kept. One document at a time, the blocks waiting to be accepted (changed since accepted, or taken in from a copy or a pull): Accept records the person's reading, for one block or a selection; what loom cannot accept says why in its row. Never accepted and accepted blocks are folded beneath, uncounted. Then every change waiting in the person's text, quilt-wide, a card each (`ChangeCard`) grouped by the document that lists it: suggestions not yet kept or discarded and, where the quilt tracks edits (`[review] track_edits`), edits made in their files since their look. Keep and Discard act as they do in the document, one change or all of a document's at once, and the last discard is undone from the bar; neither says whether the mathematics is right. To do adds, beside each document's changes, the open annotations from others, each linking to its place. Each answer is said in its row while the row stands, else in the bar.
	import '$lib/review/review.css';
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { isAgentDocument } from '$lib/manifest/documents';
	import { can, write } from '$lib/write';
	import { displayNode } from '$lib/nodes/display';
	import { anchorId, readUrl, reviewReadUrl } from '$lib/nav';
	import { causeLabel } from '$lib/review/evidence';
	import { documentsWithBlocks, notesOf } from '$lib/review/queue';
	import { acceptanceOf, todoOf, waitingIn, type BlockRow } from '$lib/review/yourChanges';
	import { acted } from '$lib/review/acted.svelte';
	import { allSays, byDocument, ready } from '$lib/review/changes';
	import { discardChanges, history, keepChanges, nextUndo, undo, type ChangeAnswer } from '$lib/review/history.svelte';
	import { itemLabel, dotVars } from '$lib/fragments/gutter';
	import { reviewRowBadge, shortDate } from '$lib/badges';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import ChangeCard from '$lib/review/ChangeCard.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';

	type Answer = { accepted?: string[]; refused?: { key: string; why: string }[] };

	/** How many rows of a list are drawn open; past it each group is folded until asked for. */
	const OPEN = 12;

	const m = $derived(store.manifest!);
	const people = $derived(m.masters.filter((x) => !x.closed && !x.context_only && !isAgentDocument(x)));
	// every pending change, by document, those just kept or discarded gone at once
	const groups = $derived(byDocument(m).map((g) => ({ ...g, changes: g.changes.filter((c) => !(c.id in acted.map)) })).filter((g) => g.changes.length));
	const changeCount = $derived(groups.reduce((n, g) => n + g.changes.length, 0));
	const todo = $derived(todoOf(m));
	const todoCount = $derived(todo.reduce((n, g) => n + g.annotations.length, 0));
	// To do: the open annotations from others, beside the changes of the document they are in, and in a group of their own where it has none
	let todoOn = $state(false);
	const todoAlone = $derived(todo.filter((t) => !groups.some((g) => g.path === t.path)));

	// the documents with blocks to accept, one at a time: asked for by name, else the first with something waiting, else the default
	const mine = $derived(documentsWithBlocks(m, people));
	const waiting = (path: string) => waitingIn(acceptanceOf(m, path));
	const doc = $derived(mine.find((x) => x.path === page.url.searchParams.get('document')) ?? mine.find((x) => waiting(x.path) > 0) ?? mine.find((x) => x.default) ?? mine[0]);
	const file = $derived(doc ? doc.path.split('/').pop()! : '');
	const y = $derived(doc ? acceptanceOf(m, doc.path) : null);
	const lists = $derived(y ? [...y.changed, ...y.taken.flatMap((t) => t.rows)] : []);
	const changedCount = $derived(y ? y.changed.length : 0);
	const takenCount = $derived(y ? y.taken.reduce((n, t) => n + t.rows.length, 0) : 0);
	const reviewer = $derived(m.reviewer?.name ?? '');
	const since = $derived(m.changes_since ? m.changes_since.when.slice(0, 16).replace('T', ' ') : '');
	// whether edits in place since the person's look wait here too, as well as suggestions
	const tracked = $derived(m.config?.review?.track_edits === true);

	let served = $state(false);
	let writes = $state({ keep: false, discard: false });
	const acts = $derived(served && !!reviewer);
	let picked = $state<Set<string>>(new Set());
	// what is running, by where it was asked: '*' for the page, a block's key, or a group's path
	let busy = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('review-accept').then((yes) => (served = yes));
		void can('change-keep').then((yes) => (writes.keep = yes));
		void can('change-discard').then((yes) => (writes.discard = yes));
	});

	const name = (key: string) => displayNode(m, key, doc?.path).name;
	const lower = (t: string) => t.charAt(0).toLowerCase() + t.slice(1);
	const part = (n: number, words: string) => (n ? `${n} ${words}` : '');

	/** Why a block changed since it was accepted: its first cause, and how many more. */
	function why(key: string): string {
		const causes = m.keys[key]?.acceptance?.causes ?? [];
		if (!causes.length) return '';
		const first = causes[0].kind === 'own-text-changed' ? 'changed since you accepted' : causeLabel(m, causes[0]);
		return first + (causes.length > 1 ? `, and ${causes.length - 1} more` : '');
	}
	const acceptable = (rows: BlockRow[]) => rows.filter((b) => b.row && !b.row.refusal).map((b) => b.key);
	function toggle(key: string): void {
		const next = new Set(picked);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		picked = next;
	}
	function toggleGroup(rows: BlockRow[]): void {
		const keys = acceptable(rows);
		const all = keys.every((k) => picked.has(k));
		const next = new Set(picked);
		for (const k of keys) {
			if (all) next.delete(k);
			else next.add(k);
		}
		picked = next;
	}
	const allPicked = (rows: BlockRow[]) => acceptable(rows).length > 0 && acceptable(rows).every((k) => picked.has(k));

	/** Whether the row asked from, a block's key, is still drawn. */
	function stands(at: string): boolean {
		const now = store.manifest;
		if (!now || !doc) return false;
		const list = acceptanceOf(now, doc.path);
		return [...list.changed, ...list.taken.flatMap((t) => t.rows), ...list.never].some((b) => b.key === at);
	}

	/** Accept `keys` at once; what loom accepts leaves its row, and each refusal is said by the block it refuses, in the row when one was pressed, in the bar for a selection. */
	async function accept(keys: string[], at: string): Promise<void> {
		busy = at;
		said = null;
		const done = (await write('review-accept', { keys })) as Awaited<ReturnType<typeof write>> & Answer;
		let text: string;
		let refused: boolean;
		if (!done.ok) {
			text = done.error?.message ?? 'The publisher refused it.';
			refused = true;
		} else {
			const ok = done.accepted ?? [];
			const no = done.refused ?? [];
			const lines = ok.length ? [ok.length === 1 ? `Accepted ${name(ok[0])}.` : `Accepted ${ok.length} blocks.`] : [];
			for (const r of no) lines.push(at === '*' ? `${name(r.key)}: ${lower(r.why)}` : r.why);
			text = lines.join('\n');
			refused = !ok.length;
			picked = new Set([...picked].filter((k) => !ok.includes(k)));
			await store.refresh();
		}
		said = { at: at !== '*' && stands(at) ? at : '*', text, refused };
		busy = '';
	}

	/** Keep or discard every ready change of one group, as the document's Changes menu does; what is refused is said in the bar. */
	async function every(how: 'keep' | 'discard', g: (typeof groups)[number]): Promise<void> {
		busy = g.path;
		said = null;
		const which = g.document ? { all: true as const, document: g.path } : { changes: g.changes.filter(ready).map((c) => c.id) };
		const res: ChangeAnswer = how === 'keep' ? await keepChanges(which) : await discardChanges(which);
		const done = res.done?.length;
		const refused = res.refused ?? [];
		const verb = how === 'keep' ? 'Kept' : 'Discarded';
		const text = !res.ok ? (res.error?.message ?? 'The publisher refused it.') : [done !== undefined ? `${verb} ${done} ${done === 1 ? 'change' : 'changes'} in ${g.label}.` : `${verb} the changes in ${g.label}.`, ...refused.map((r) => r.why)].join('\n');
		said = { at: '*', text, refused: !res.ok || (done === 0 && refused.length > 0) };
		busy = '';
	}

	/** Undo the last discard, saying loom's refusal where there is one. */
	async function back(): Promise<void> {
		const why = await undo();
		said = why ? { at: '*', text: why, refused: true } : null;
	}

	// a link to one block's row (a block's "See this block in Review") opens the fold it is in
	$effect(() => {
		const hash = page.url.hash.slice(1);
		if (!hash || !y) return;
		void tick().then(() => {
			const row = window.document.getElementById(hash);
			const fold = row?.closest('details');
			if (fold && !fold.open) fold.open = true;
			row?.scrollIntoView({ block: 'center' });
		});
	});
</script>

{#snippet todoRows(list: import('$lib/manifest/types').Annotation[])}
	<ul class="todo" data-testid="todo-list">
		{#each list as a (a.id)}
			<li data-testid="todo-row" data-annotation={a.id}>
				<span class="dot" style={dotVars(a)}></span>
				<a href="quilt:{a.id}" data-testid="todo-open">{itemLabel(m, a)}</a>
				<span class="of">{shortDate(a.created)}</span>
			</li>
		{/each}
	</ul>
{/snippet}

{#snippet blockRow(b: BlockRow)}
	{@const r = b.row}
	{@const cause = r?.cause === 'earlier-change' ? why(b.key) || 'changed since you accepted' : ''}
	{@const context = displayNode(m, b.key, doc?.path).context}
	<li class="block" id={`review-${anchorId(b.key)}`} data-testid="review-row" data-key={b.key}>
		<div class="line">
			{#if acts && r}<input type="checkbox" disabled={!!r.refusal} checked={picked.has(b.key)} onchange={() => toggle(b.key)} aria-label={`Select ${name(b.key)}`} data-testid="review-pick" />{/if}
			<a class="name" href={reviewReadUrl(doc!.path, b.key)}>{name(b.key)}</a>
			{#if context}<span class="of">{context}</span>{/if}
			{#if cause}<span class="tag changed" data-testid="tag-changed">{cause}</span>{/if}
			{#each notesOf(m, b.key) as note (note)}<a class="note" href={reviewReadUrl(doc!.path, b.key)} data-testid="review-note">{note}</a>{/each}
			<span class="acts">
				{#if r}<a class="btn quiet small" href={reviewReadUrl(doc!.path, b.key, cause ? 0 : undefined)} data-testid="review-read">{cause ? 'See change' : 'Read'}</a>{/if}
				{#if acts && r && !r.refusal}<button class="btn small primary" disabled={!!busy} onclick={() => void accept([b.key], b.key)} data-testid="review-accept">{busy === b.key ? 'Accepting…' : 'Accept'}</button>{/if}
			</span>
		</div>
		{#if r?.refusal}<p class="cannot" data-testid="review-refusal">Can't be accepted yet: {lower(r.refusal)}</p>{/if}
		{#if said?.at === b.key}<Said text={said.text} refused={said.refused} testid="review-said" />{/if}
	</li>
{/snippet}

{#snippet group(id: string, title: string, rows: BlockRow[], open: boolean)}
	<details {open} class="group" data-testid="review-group" data-group={id}>
		<summary>
			{#if acts && acceptable(rows).length}<input type="checkbox" checked={allPicked(rows)} onclick={(e) => e.stopPropagation()} onchange={() => toggleGroup(rows)} aria-label={`Select every block ${title.toLowerCase()} that can be accepted`} data-testid="review-pick-group" />{/if}
			<span class="title">{title}</span> <span class="count" data-testid="review-group-count">{rows.length}</span>
		</summary>
		<ul>{#each rows as b (b.key)}{@render blockRow(b)}{/each}</ul>
	</details>
{/snippet}

<main class="page review-page scrollbar-shown" data-testid="your-changes">
	<ReviewHeading title="Your Changes">{#snippet aside()}<HelpDot label="what the Your Changes page shows" topic="review" />{/snippet}</ReviewHeading>
	<ActionBar said={said?.at === '*' ? said.text : ''} refused={said?.refused} testid="review-bar">
		{#snippet lead()}
			<span class="muted" data-testid="review-summary">{[part(changedCount, 'changed since you accepted'), part(takenCount, 'taken in'), part(changeCount, changeCount === 1 ? 'change waiting' : 'changes waiting'), reviewer ? `reviewing as ${reviewer}` : ''].filter(Boolean).join(' · ') || 'Nothing waits'}</span>
		{/snippet}
		{#snippet actions()}
			<!-- a discard, here or in a document, is undone as the document's toolbar undoes it -->
			{#if nextUndo().startsWith('discard')}<button type="button" class="btn small quiet" disabled={history.busy} data-testid="review-undo" onclick={() => void back()}>Undo {nextUndo()}</button>{/if}
			<button type="button" class="btn small" class:on={todoOn} aria-pressed={todoOn} title="To do: the open annotations from others, beside the changes" data-testid="your-todo" onclick={() => (todoOn = !todoOn)}>To do <span class="badge">{changeCount + todoCount}</span></button>
			{#if acts && picked.size}
				<span data-testid="review-picked">{picked.size} selected</span>
				<button class="btn primary" disabled={!!busy} onclick={() => void accept([...picked], '*')} data-testid="review-accept-picked">{busy === '*' ? 'Accepting…' : `Accept ${picked.size}`}</button>
				<button class="btn quiet" onclick={() => (picked = new Set())} data-testid="review-clear">Clear</button>
			{/if}
		{/snippet}
	</ActionBar>
	<p class="lead">The mathematics first: the blocks of your documents changed since you accepted them, or taken in from a copy or a pull, and <b>Accept</b> records that you have read one and vouch for it. Then what waits to be kept: {tracked ? `suggestions not yet kept or discarded, and every edit made in your files since your look${since ? ` of ${since}` : ''}` : 'suggestions not yet kept or discarded'}. <b>Keep</b> one to take it into your text, or <b>Discard</b> it {tracked ? 'to put your words back or drop the suggestion' : 'to drop it'}; neither says whether the mathematics is right.</p>

	<h2 class="part">Waiting to be accepted</h2>
	{#if !reviewer}<p class="muted" data-testid="review-no-reviewer">Choose your reviewer name in Settings to accept.</p>
	{:else if !served}<p class="muted" data-testid="review-read-only">This copy of the quilt only reads; accepting needs the quilt served for writing.</p>{/if}
	{#if !mine.length}<NoDrafts what="blocks to review" />
	{:else if y && doc}
		<p class="pick">
			{#if mine.length > 1}<select aria-label="Document" data-testid="review-document" value={doc.path} onchange={(e) => goto(`?document=${encodeURIComponent(e.currentTarget.value)}`)}>{#each mine as d (d.path)}<option value={d.path}>{d.path.split('/').pop()}{waiting(d.path) ? ` · ${waiting(d.path)}` : ''}</option>{/each}</select>{:else}<strong>{file}</strong>{/if}
		</p>
		{#if !lists.length && !y.never.length}<Empty text={`Every block of ${file} is accepted.`} testid="review-empty" />{/if}
		{#if y.changed.length}{@render group('changed', 'Changed', y.changed, y.changed.length <= OPEN)}{/if}
		{#each y.taken as t (t.label)}{@render group('taken', t.label, t.rows, true)}{/each}
		{#if y.never.length}{@render group('never', 'Never accepted', y.never, false)}{/if}
		{#if y.accepted.length}
			<details class="group" data-testid="review-group" data-group="accepted">
				<summary><span class="title">Accepted</span> <span class="count" data-testid="review-group-count">{y.accepted.length}</span></summary>
				<ul>
					{#each y.accepted as k (k.key)}
						<li class="block" id={`review-${anchorId(k.key)}`} data-testid="review-row" data-key={k.key}>
							<div class="line">
								<a class="name" href={readUrl(doc.path, k.key)}>{name(k.key)}</a>
								<Badge parts={reviewRowBadge(m, k)} />
								{#if k.acceptance}<span class="of">by {k.acceptance.author}, {shortDate(k.acceptance.date)}</span>{/if}
							</div>
						</li>
					{/each}
				</ul>
			</details>
		{/if}
	{/if}

	<h2 class="part">Changes to keep</h2>
	<section class="changes" data-testid="your-change-list">
		{#each groups as g (g.path)}
			{@const says = allSays(g.changes.filter(ready))}
			{@const n = g.changes.filter(ready).length}
			<section class="cgroup" data-testid="change-group" data-path={g.path}>
				<div class="chead">
					<span class="title">{g.label}</span>
					<span class="count" data-testid="change-group-count">{g.changes.length}</span>
					{#if !g.document}<span class="muted">in no document's text</span>{/if}
					<span class="acts">
						<button type="button" class="btn small" disabled={!n || !writes.keep || !!busy} title={says.keep} data-testid="group-keep-all" onclick={() => void every('keep', g)}>{busy === g.path ? 'Working…' : `Keep all ${n}`}</button>
						<button type="button" class="btn small quiet" disabled={!n || !writes.discard || !!busy} title={says.discard} data-testid="group-discard-all" onclick={() => void every('discard', g)}>Discard all {n}</button>
					</span>
				</div>
				<div class="cards">{#each g.changes as c (c.id)}<ChangeCard {c} place />{/each}</div>
				{#if todoOn}
					{@const here = todo.find((t) => t.path === g.path)}
					{#if here}{@render todoRows(here.annotations)}{/if}
				{/if}
			</section>
		{:else}
			<Empty text="No changes wait in your text." testid="changes-empty" />
		{/each}
		{#if todoOn}
			{#each todoAlone as t (t.path)}
				<section class="cgroup" data-testid="todo-group" data-path={t.path}>
					<div class="chead"><span class="title">{t.label}</span><span class="count">{t.annotations.length}</span><span class="muted">open annotations from others</span></div>
					{@render todoRows(t.annotations)}
				</section>
			{/each}
			{#if !todoCount}<p class="muted" data-testid="todo-none">No open annotations from others.</p>{/if}
		{/if}
	</section>
</main>

<style>
	.lead {
		margin: 0 0 var(--gap);
		font-size: 13px;
		color: var(--ink-soft);
	}
	.lead b {
		font-weight: 500;
		color: var(--ink);
	}
	.changes {
		display: grid;
		gap: var(--gap);
		margin: 0 0 var(--gap-wide);
	}
	.cgroup {
		display: grid;
		gap: 8px;
		min-width: 0;
	}
	.chead {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px 10px;
		font-size: 13.5px;
	}
	.chead .title {
		font-weight: 600;
	}
	.chead .count {
		color: var(--ink-soft);
		font-variant-numeric: tabular-nums;
	}
	.cards {
		display: grid;
		gap: 8px;
		min-width: 0;
	}
	.todo {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 4px;
		font-size: 13px;
	}
	.todo li {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.todo .dot {
		flex: none;
		width: 10px;
		height: 10px;
		box-sizing: border-box;
		background: var(--fill);
		border: 1.5px solid var(--edge);
		border-radius: 50%;
	}
	.todo a {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.part {
		margin: var(--gap-wide) 0 var(--gap-tight);
		font-size: 15px;
		font-weight: 600;
	}
	.pick {
		margin: 0 0 var(--gap-tight);
	}
	.group {
		margin: 0 0 var(--gap);
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--review-paper);
	}
	.group > summary {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 14px;
		cursor: pointer;
		font-size: 13.5px;
	}
	.group > summary .count {
		color: var(--ink-soft);
		font-variant-numeric: tabular-nums;
	}
	.group ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.block {
		border-top: 1px solid var(--rule);
		padding: 8px 14px;
	}
	.line {
		display: flex;
		align-items: baseline;
		gap: 4px 10px;
		flex-wrap: wrap;
	}
	.line input {
		align-self: center;
	}
	.name {
		font-size: 14px;
		overflow-wrap: anywhere;
	}
	.of,
	.note {
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.tag {
		padding: 1px 8px;
		border-radius: 999px;
		background: var(--leaf);
		color: var(--ink-soft);
		font-size: 11.5px;
	}
	.tag.changed {
		background: var(--state-stale-wash, var(--leaf));
		color: var(--state-stale);
	}
	.acts {
		margin-left: auto;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.cannot {
		margin: 4px 0 0;
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.muted {
		color: var(--ink-soft);
		font-size: 12.5px;
	}
	.badge {
		min-width: 16px;
		padding: 0 5px;
		font-size: 10.5px;
		line-height: 15px;
		text-align: center;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: 8px;
	}
	select {
		max-width: 100%;
	}
</style>
