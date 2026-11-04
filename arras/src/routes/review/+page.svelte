<script lang="ts">
	// Review › Your Changes: what changed in the person's text and what waits for their word on it, one document at a time. A block is listed once, with every reason it waits: edited since their look (Keep takes it into the look, Undo puts it back after asking, the text it replaces kept first), changed since they accepted it or taken in from a copy or a pull (Accept records their reading, for one block or a selection, and keeps its edit too). Keep says nothing about the mathematics, so a kept block still waits. Text edited outside any block, and files in no document, are kept or undone and have nothing to accept. Never accepted and accepted blocks are folded beneath, uncounted. What loom cannot accept says why in its row, before anything is pressed; each answer is said in its row while the row stands, else in the bar.
	import '$lib/review/review.css';
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { isAgentDocument } from '$lib/manifest/documents';
	import type { FileChange } from '$lib/manifest/types';
	import { can, write } from '$lib/write';
	import { displayNode } from '$lib/nodes/display';
	import { anchorId, readUrl, reviewReadUrl } from '$lib/nav';
	import { documentKeys } from '$lib/review/documents';
	import { causeLabel } from '$lib/review/evidence';
	import { documentsWithBlocks, notesOf } from '$lib/review/queue';
	import { otherFiles, waitingIn, yourChangesOf, type BlockRow, type Edit } from '$lib/review/yourChanges';
	import { reviewRowBadge, shortDate } from '$lib/badges';
	import { fileHref } from '$lib/shell/files';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import EditView from '$lib/review/EditView.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';

	type Answer = { accepted?: string[]; refused?: { key: string; why: string }[] };
	type Verb = 'changes-keep' | 'changes-undo';

	/** How many rows of a list draw their edits open; past it each is folded until asked for. */
	const OPEN = 12;
	const WHAT: Record<string, string> = { changed: 'changed', new: 'new since your look', gone: 'gone since your look' };

	const m = $derived(store.manifest!);
	const others = $derived(otherFiles(m));
	const people = $derived(m.masters.filter((x) => !x.closed && !x.context_only && !isAgentDocument(x)));
	// the person's documents with something to list: a block, or an edit
	const mine = $derived.by(() => {
		const withBlocks = new Set(documentsWithBlocks(m, people).map((d) => d.path));
		for (const c of m.changes ?? []) for (const d of c.documents ?? []) withBlocks.add(d);
		return people.filter((d) => withBlocks.has(d.path));
	});
	const waiting = (path: string) => waitingIn(yourChangesOf(m, path));
	// asked for by name, else the first with something waiting, else the default
	const doc = $derived(mine.find((x) => x.path === page.url.searchParams.get('document')) ?? mine.find((x) => waiting(x.path) > 0) ?? mine.find((x) => x.default) ?? mine[0]);
	const file = $derived(doc ? doc.path.split('/').pop()! : '');
	const y = $derived(doc ? yourChangesOf(m, doc.path) : null);
	const lists = $derived(y ? [...y.changed, ...y.taken.flatMap((t) => t.rows)] : []);
	const editedCount = $derived(lists.filter((b) => b.edit || b.editedWith).length + (y?.outside.length ?? 0) + others.length);
	const changedCount = $derived(y ? y.changed.filter((b) => b.row?.cause === 'earlier-change').length : 0);
	const takenCount = $derived(y ? y.taken.reduce((n, t) => n + t.rows.length, 0) : 0);
	const reviewer = $derived(m.reviewer?.name ?? '');
	const since = $derived(m.changes_since ? m.changes_since.when.slice(0, 16).replace('T', ' ') : '');

	let served = $state(false);
	let keeping = $state(false);
	const acts = $derived(served && !!reviewer);
	let picked = $state<Set<string>>(new Set());
	// what is running, by where it was asked: '*' for the page, a block's key, a file's path, or `at#n` for one change
	let busy = $state('');
	let asking = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('review-accept').then((yes) => (served = yes));
		void can('changes-keep').then((yes) => (keeping = yes));
	});

	const name = (key: string) => displayNode(m, key, doc?.path).name;
	const lower = (t: string) => t.charAt(0).toLowerCase() + t.slice(1);
	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');
	const part = (n: number, words: string) => (n ? `${n} ${words}` : '');

	/** Why a block changed since it was accepted: its first cause, and how many more. */
	function why(key: string): string {
		const causes = m.keys[key]?.acceptance?.causes ?? [];
		if (!causes.length) return '';
		// its own text changed reads apart from an edit since the look, which the row may also carry
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

	/** Whether the row asked from, a block's key or a file's path, is still drawn. */
	function stands(at: string): boolean {
		const now = store.manifest;
		if (!now || !doc) return false;
		const list = yourChangesOf(now, doc.path);
		return (
			[...list.changed, ...list.taken.flatMap((t) => t.rows), ...list.never].some((b) => b.key === at) ||
			list.outside.some((e) => e.change.path === at) ||
			otherFiles(now).some((c) => c.path === at)
		);
	}

	/** Accept `keys` at once; what loom accepts leaves its row with its edit, and each refusal is said by the block it refuses, in the row when one was pressed, in the bar for a selection. */
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

	/** Keep or undo every edit, or some of one file's, against the file as this page drew it; the buttons stay busy until the page has been drawn again, so a row that is going is never left live. */
	async function act(verb: Verb, at: string, change?: FileChange, hunks?: number[]): Promise<void> {
		busy = at;
		asking = '';
		said = null;
		const body: Record<string, unknown> = {};
		if (change) {
			body.path = change.path;
			if (change.hash) body.seen = change.hash;
			if (hunks && hunks.length < (change.hunks ?? 0)) body.hunks = hunks;
		}
		const done = await write(verb, body);
		if (done.ok || done.error?.code === 'stale') await store.refresh();
		const stale = done.error?.code === 'stale';
		const text = done.ok ? capital(done.result ?? 'done') : stale ? 'This file changed since the page was drawn; it is drawn again now.' : (done.error?.message ?? 'The publisher refused it.');
		const row = at.split('#')[0];
		said = { at: at !== '*' && stands(row) ? row : '*', text, refused: !done.ok };
		busy = '';
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
			// the diffs above it draw as they arrive and push it down, so it is held in view until they have
			if (!row) return;
			const held = new ResizeObserver(() => row.scrollIntoView({ block: 'center' }));
			for (const g of window.document.querySelectorAll('.group')) held.observe(g);
			setTimeout(() => held.disconnect(), 1500);
		});
	});
</script>

<!-- The diff of one row's edit, each of several changes with its own Keep and Undo. -->
{#snippet editOf(e: Edit, at: string, folded: boolean)}
	{#snippet hunk(n: number)}
		{@const here = `${at}#${n}`}
		{#if keeping}
			{#if asking === here}
				<span data-testid="hunk-ask">Put this change back? Its text now is kept.</span>
				<button class="btn small primary" onclick={() => act('changes-undo', here, e.change, [n])} disabled={!!busy} data-testid="hunk-undo-go">Undo</button>
				<button class="btn small quiet" onclick={() => (asking = '')}>Cancel</button>
			{:else}
				<button class="btn small" onclick={() => act('changes-keep', here, e.change, [n])} disabled={!!busy} data-testid="hunk-keep">{busy === here ? 'Keeping…' : 'Keep'}</button>
				<button class="btn small" onclick={() => (asking = here)} disabled={!!busy} data-testid="hunk-undo">Undo…</button>
			{/if}
		{/if}
	{/snippet}
	<EditView edit={e} {folded} {hunk} />
{/snippet}

<!-- Keep and Undo for all of a row's edit; Undo asks first. -->
{#snippet editActs(e: Edit, at: string, what: string)}
	{#if keeping}
		{#if asking === at}
			<span class="ask" data-testid="undo-ask">{`Put ${what} back as it was at your look? Its text now is kept.`}</span>
			<button class="btn small primary" onclick={() => act('changes-undo', at, e.change, e.hunks)} disabled={!!busy} data-testid="undo-go">Undo</button>
			<button class="btn small quiet" onclick={() => (asking = '')} data-testid="undo-cancel">Cancel</button>
		{:else}
			<button class="btn small" onclick={() => act('changes-keep', at, e.change, e.hunks)} disabled={!!busy} data-testid="edit-keep">{busy === at ? 'Working…' : 'Keep'}</button>
			<button class="btn small quiet" onclick={() => (asking = at)} disabled={!!busy} data-testid="edit-undo">Undo…</button>
		{/if}
	{/if}
{/snippet}

{#snippet blockRow(b: BlockRow, folded: boolean)}
	{@const r = b.row}
	{@const cause = r?.cause === 'earlier-change' ? why(b.key) || 'changed since you accepted' : ''}
	{@const edited = !!b.edit || !!b.editedWith}
	{@const context = displayNode(m, b.key, doc?.path).context}
	<li class="block" id={`review-${anchorId(b.key)}`} data-testid="review-row" data-key={b.key}>
		<div class="line">
			{#if acts && r}<input type="checkbox" disabled={!!r.refusal} checked={picked.has(b.key)} onchange={() => toggle(b.key)} aria-label={`Select ${name(b.key)}`} data-testid="review-pick" />{/if}
			<a class="name" href={reviewReadUrl(doc!.path, b.key)}>{name(b.key)}</a>
			{#if context}<span class="of">{context}</span>{/if}
			{#if b.edit}<span class="tag edit" data-testid="tag-edited">edited since your look</span>{/if}
			{#if b.editedWith}<span class="tag edit" data-testid="tag-edited-with">edited with <a href={`#review-${anchorId(b.editedWith)}`}>{name(b.editedWith)}</a></span>{/if}
			{#if cause}<span class="tag changed" data-testid="tag-changed">{cause}</span>{/if}
			{#if edited && r?.cause === 'never-accepted'}<span class="tag" data-testid="tag-never">never accepted</span>{/if}
			{#each notesOf(m, b.key) as note (note)}<a class="note" href={reviewReadUrl(doc!.path, b.key)} data-testid="review-note">{note}</a>{/each}
			<span class="acts">
				{#if b.edit}{@render editActs(b.edit, b.key, name(b.key))}{/if}
				{#if !b.edit && r}<a class="btn quiet small" href={reviewReadUrl(doc!.path, b.key, cause ? 0 : undefined)} data-testid="review-read">{cause ? 'See change' : 'Read'}</a>{/if}
				{#if acts && r && !r.refusal}<button class="btn small primary" disabled={!!busy} onclick={() => void accept([b.key], b.key)} data-testid="review-accept">{busy === b.key ? 'Accepting…' : 'Accept'}</button>{/if}
			</span>
		</div>
		{#if r?.refusal}<p class="cannot" data-testid="review-refusal">Can't be accepted yet: {lower(r.refusal)}</p>{/if}
		{#if b.edit}{@render editOf(b.edit, b.key, folded)}{/if}
		{#if said?.at === b.key}<Said text={said.text} refused={said.refused} testid="review-said" />{/if}
	</li>
{/snippet}

{#snippet group(id: string, title: string, rows: BlockRow[], open: boolean, folded: boolean)}
	<details {open} class="group" data-testid="review-group" data-group={id}>
		<summary>
			{#if acts && acceptable(rows).length}<input type="checkbox" checked={allPicked(rows)} onclick={(e) => e.stopPropagation()} onchange={() => toggleGroup(rows)} aria-label={`Select every block ${title.toLowerCase()} that can be accepted`} data-testid="review-pick-group" />{/if}
			<span class="title">{title}</span> <span class="count" data-testid="review-group-count">{rows.length}</span>
		</summary>
		<ul>{#each rows as b (b.key)}{@render blockRow(b, folded)}{/each}</ul>
	</details>
{/snippet}

<main class="page review-page scrollbar-shown" data-testid="your-changes">
	<ReviewHeading title="Your Changes">{#snippet aside()}<HelpDot label="what the Your Changes page shows" topic="review" />{/snippet}</ReviewHeading>
	<ActionBar said={said?.at === '*' ? said.text : ''} refused={said?.refused} testid="review-bar">
		{#snippet lead()}
			{#if mine.length > 1 && doc}<select aria-label="Document" data-testid="review-document" value={doc.path} onchange={(e) => goto(`?document=${encodeURIComponent(e.currentTarget.value)}`)}>{#each mine as d (d.path)}<option value={d.path}>{d.path.split('/').pop()}{waiting(d.path) ? ` · ${waiting(d.path)}` : ''}</option>{/each}</select>{:else if doc}<strong>{file}</strong>{/if}
			{#if y}
				<span class="muted" data-testid="review-summary">{[part(waitingIn(y) + others.length, 'waiting'), part(editedCount, 'edited since your look'), part(changedCount, 'changed since you accepted'), part(takenCount, 'taken in'), reviewer ? `reviewing as ${reviewer}` : ''].filter(Boolean).join(' · ') || 'Nothing waits'}</span>
			{/if}
		{/snippet}
		{#snippet actions()}
			{#if keeping && (m.changes ?? []).length}<button class="btn" disabled={!!busy} onclick={() => act('changes-keep', '*')} title="Take every edit into your look; nothing about the mathematics is said" data-testid="changes-keep-all">{busy === '*' && !picked.size ? 'Keeping…' : 'Keep every edit'}</button>{/if}
			{#if acts && picked.size}
				<span data-testid="review-picked">{picked.size} selected</span>
				<button class="btn primary" disabled={!!busy} onclick={() => void accept([...picked], '*')} data-testid="review-accept-picked">{busy === '*' ? 'Accepting…' : `Accept ${picked.size}`}</button>
				<button class="btn quiet" onclick={() => (picked = new Set())} data-testid="review-clear">Clear</button>
			{/if}
		{/snippet}
	</ActionBar>
	<p class="lead">What changed in your text{since ? ` since your look, ${since}` : ''}. <b>Keep</b> an edit once you have seen it, or <b>Undo</b> it; neither says whether the mathematics is right. <b>Accept</b> a block to vouch for its mathematics, which keeps its edit too. A block is listed once, with every reason it waits.</p>
	{#if !reviewer}<p class="muted" data-testid="review-no-reviewer">Choose your reviewer name in Settings to accept.</p>
	{:else if !served}<p class="muted" data-testid="review-read-only">This copy of the quilt only reads; accepting needs the quilt served for writing.</p>{/if}
	{#if !mine.length}<NoDrafts what="blocks to review" />
	{:else if y}
		{#if !lists.length && !y.outside.length && !y.never.length}<Empty text={`Every block of ${file} is accepted.`} testid="review-empty" />{/if}
		{#if y.changed.length}{@render group('changed', 'Changed', y.changed, true, y.changed.length > OPEN)}{/if}
		{#each y.taken as t (t.label)}{@render group('taken', t.label, t.rows, true, true)}{/each}
		{#if y.outside.length}
			<details open class="group" data-testid="review-group" data-group="outside">
				<summary><span class="title">Outside any block</span> <span class="count" data-testid="review-group-count">{y.outside.length}</span></summary>
				<ul>
					{#each y.outside as e (e.change.path)}
						<li class="block" data-testid="outside-row" data-path={e.change.path}>
							<div class="line">
								<code class="path">{e.change.path}</code>
								<span class="tag edit">edited since your look</span>
								<span class="acts">{@render editActs(e, e.change.path, 'this text')}</span>
							</div>
							{@render editOf(e, e.change.path, false)}
							{#if said?.at === e.change.path}<Said text={said.text} refused={said.refused} testid="review-said" />{/if}
						</li>
					{/each}
				</ul>
			</details>
		{/if}
	{/if}
	{#if others.length}
		<details open class="group" data-testid="review-group" data-group="others">
			<summary><span class="title">Other files</span> <span class="count" data-testid="review-group-count">{others.length}</span> <span class="muted">in no document's text, so nothing to accept</span></summary>
			<ul>
				{#each others as c (c.path)}
					{@const f = (m.files ?? []).find((x) => x.path === c.path)}
					{@const several = (c.hunks ?? 0) > 1}
					<li class="block" data-testid="change" data-path={c.path}>
						<div class="line">
							{#if c.kind !== 'gone' && f}<a class="path" href={fileHref(m, f)} data-testid="change-open">{c.path}</a>{:else}<code class="path">{c.path}</code>{/if}
							<span class="tag edit">{WHAT[c.kind] ?? c.kind}{several ? ` · ${c.hunks} changes` : ''}</span>
							{#if keeping}
								<span class="acts">
									{#if asking === c.path}
										<span class="ask" data-testid="undo-ask">{c.kind === 'new' ? `Remove ${c.path}? Its text is kept.` : `Put ${c.path} back as it was at your look? Its text now is kept.`}</span>
										<button class="btn small primary" onclick={() => act('changes-undo', c.path, c)} disabled={!!busy} data-testid="undo-go">{c.kind === 'new' ? 'Remove' : 'Undo'}</button>
										<button class="btn small quiet" onclick={() => (asking = '')} data-testid="undo-cancel">Cancel</button>
									{:else}
										<button class="btn small" onclick={() => act('changes-keep', c.path, c)} disabled={!!busy} data-testid="change-keep">{busy === c.path ? 'Working…' : several ? 'Keep all of it' : 'Keep'}</button>
										<button class="btn small quiet" onclick={() => (asking = c.path)} disabled={!!busy} data-testid="change-undo">{c.kind === 'new' ? 'Remove…' : several ? 'Undo all of it…' : 'Undo…'}</button>
									{/if}
								</span>
							{/if}
						</div>
						{#if c.diff}{@render editOf({ change: c, hunks: Array.from({ length: c.hunks ?? 0 }, (_, n) => n) }, c.path, false)}{/if}
						{#if said?.at === c.path}<Said text={said.text} refused={said.refused} testid="change-said" />{/if}
					</li>
				{/each}
			</ul>
		</details>
	{/if}
	{#if y}
		{#if y.never.length}{@render group('never', 'Never accepted', y.never, false, true)}{/if}
		{#if y.accepted.length}
			<details class="group" data-testid="review-group" data-group="accepted">
				<summary><span class="title">Accepted</span> <span class="count" data-testid="review-group-count">{y.accepted.length}</span></summary>
				<ul>
					{#each y.accepted as k (k.key)}
						<li class="block" id={`review-${anchorId(k.key)}`} data-testid="review-row" data-key={k.key}>
							<div class="line">
								<a class="name" href={readUrl(doc!.path, k.key)}>{name(k.key)}</a>
								<Badge parts={reviewRowBadge(m, k)} />
								{#if k.acceptance}<span class="of">by {k.acceptance.author}, {shortDate(k.acceptance.date)}</span>{/if}
							</div>
						</li>
					{/each}
				</ul>
			</details>
		{/if}
	{/if}
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
	.path {
		font-family: var(--mono);
		font-size: 12.5px;
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
	.tag.edit {
		background: var(--link-wash);
		color: var(--link);
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
	.ask {
		font-size: 12.5px;
		color: var(--ink);
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
	select {
		max-width: 100%;
	}
</style>
