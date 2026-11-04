<script lang="ts">
	// Review › Needs review: one document's blocks not freshly accepted, by why they wait (changed since accepted, taken in, never accepted), each accepted in its row or several at once; those accepted are folded beneath. Read opens a block in its document, with the panel that says why it waits beside it. What loom cannot accept says why in its row, before anything is pressed.
	import '$lib/review/review.css';
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { isAgentDocument } from '$lib/manifest/documents';
	import type { UnresolvedReview } from '$lib/manifest/types';
	import { can, write } from '$lib/write';
	import { displayNode } from '$lib/nodes/display';
	import { anchorId, readUrl, reviewReadUrl } from '$lib/nav';
	import { documentKeys } from '$lib/review/documents';
	import { causeLabel } from '$lib/review/evidence';
	import { documentsWithBlocks, groupsOf, notesOf } from '$lib/review/queue';
	import { reviewRowBadge, shortDate } from '$lib/badges';
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import HelpDot from '$lib/components/HelpDot.svelte';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';

	type Answer = { accepted?: string[]; refused?: { key: string; why: string }[] };

	const m = $derived(store.manifest!);
	const mine = $derived(documentsWithBlocks(m, m.masters.filter((x) => !x.closed && !x.context_only && !isAgentDocument(x))));
	// asked for by name, else the first holding what Review counts (changed or taken in), else the default
	const counted = (path: string) => {
		const g = groupsOf(m, path);
		return g.changed.length + g.taken.length > 0;
	};
	const doc = $derived(mine.find((x) => x.path === page.url.searchParams.get('document')) ?? mine.find((x) => counted(x.path)) ?? mine.find((x) => x.default) ?? mine[0]);
	const file = $derived(doc ? doc.path.split('/').pop()! : '');
	const groups = $derived(doc ? groupsOf(m, doc.path) : null);
	const blocks = $derived(doc ? documentKeys(m, doc.path).filter((k) => k.kind === 'statement' || k.kind === 'proof').length : 0);
	const waiting = $derived(groups ? groups.changed.length + groups.taken.reduce((n, t) => n + t.rows.length, 0) + groups.never.length : 0);
	const reviewer = $derived(m.reviewer?.name ?? '');
	let served = $state(false);
	const acts = $derived(served && !!reviewer);
	let picked = $state<Set<string>>(new Set());
	// what is running, by where it was asked: '*' for the selection, else a block's key
	let busy = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('review-accept').then((yes) => (served = yes));
	});

	const name = (key: string) => displayNode(m, key, doc?.path).name;
	const lower = (t: string) => t.charAt(0).toLowerCase() + t.slice(1);
	/** Why a block changed since it was accepted: its first cause, and how many more. */
	function why(r: UnresolvedReview): string {
		const causes = m.keys[r.key]?.acceptance?.causes ?? [];
		if (!causes.length) return '';
		return causeLabel(m, causes[0]) + (causes.length > 1 ? `, and ${causes.length - 1} more` : '');
	}
	function toggle(key: string): void {
		const next = new Set(picked);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		picked = next;
	}
	function toggleGroup(rows: UnresolvedReview[]): void {
		const keys = rows.filter((r) => !r.refusal).map((r) => r.key);
		const all = keys.every((k) => picked.has(k));
		const next = new Set(picked);
		for (const k of keys) {
			if (all) next.delete(k);
			else next.add(k);
		}
		picked = next;
	}
	const allPicked = (rows: UnresolvedReview[]) => rows.some((r) => !r.refusal) && rows.filter((r) => !r.refusal).every((r) => picked.has(r.key));

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
		const still = at !== '*' && (store.manifest?.unresolved ?? []).some((r) => r.key === at);
		said = { at: still ? at : '*', text, refused };
		busy = '';
	}

	// a link to one block's row (a block's "See this block in Review") opens the fold it is in
	$effect(() => {
		const hash = page.url.hash.slice(1);
		if (!hash || !groups) return;
		void tick().then(() => {
			const row = window.document.getElementById(hash);
			const fold = row?.closest('details');
			if (fold && !fold.open) fold.open = true;
			row?.scrollIntoView({ block: 'center' });
		});
	});
</script>

{#snippet row(r: UnresolvedReview, see: boolean)}
	<li class="block" id={`review-${anchorId(r.key)}`} data-testid="review-row" data-key={r.key}>
		<div class="line">
			{#if acts}<input type="checkbox" disabled={!!r.refusal} checked={picked.has(r.key)} onchange={() => toggle(r.key)} aria-label={`Select ${name(r.key)}`} data-testid="review-pick" />{/if}
			<a class="name" href={reviewReadUrl(doc!.path, r.key)}>{name(r.key)}</a>
			{#if see && why(r)}<span class="why">{why(r)}</span>{/if}
			{#each notesOf(m, r.key) as note (note)}<a class="note" href={reviewReadUrl(doc!.path, r.key)} data-testid="review-note">{note}</a>{/each}
			<span class="acts">
				<a class="btn quiet small" href={reviewReadUrl(doc!.path, r.key, see ? 0 : undefined)} data-testid="review-read">{see ? 'See change' : 'Read'}</a>
				{#if acts && !r.refusal}<button class="btn small" disabled={!!busy} onclick={() => void accept([r.key], r.key)} data-testid="review-accept">{busy === r.key ? 'Accepting…' : 'Accept'}</button>{/if}
			</span>
		</div>
		{#if r.refusal}<p class="cannot" data-testid="review-refusal">Can't be accepted yet: {lower(r.refusal)}</p>{/if}
		{#if said?.at === r.key}<Said text={said.text} refused={said.refused} testid="review-said" />{/if}
	</li>
{/snippet}

{#snippet group(id: string, title: string, rows: UnresolvedReview[], see: boolean)}
	<details open class="group" data-testid="review-group" data-group={id}>
		<summary>
			{#if acts && rows.some((r) => !r.refusal)}<input type="checkbox" checked={allPicked(rows)} onclick={(e) => e.stopPropagation()} onchange={() => toggleGroup(rows)} aria-label={`Select every block ${title.toLowerCase()} that can be accepted`} data-testid="review-pick-group" />{/if}
			<span class="title">{title}</span> <span class="count" data-testid="review-group-count">{rows.length}</span>
		</summary>
		<ul>{#each rows as r (r.key)}{@render row(r, see)}{/each}</ul>
	</details>
{/snippet}

<main class="page review-page">
	<ReviewHeading title="Needs review">{#snippet aside()}<HelpDot label="what needs review shows" topic="review" />{/snippet}</ReviewHeading>
	{#if !mine.length}<NoDrafts what="blocks to review" />
	{:else if doc && groups}
		<ActionBar said={said?.at === '*' ? said.text : ''} refused={said?.refused} testid="review-bar">
			{#snippet lead()}
				{#if mine.length > 1}<select aria-label="Document" data-testid="review-document" value={doc.path} onchange={(e) => goto(`?document=${encodeURIComponent(e.currentTarget.value)}`)}>{#each mine as d (d.path)}<option value={d.path}>{d.path.split('/').pop()}</option>{/each}</select>{:else}<strong>{file}</strong>{/if}
				<span class="muted" data-testid="review-summary">{blocks} {blocks === 1 ? 'block' : 'blocks'}, {waiting} not accepted{reviewer ? ` · reviewing as ${reviewer}` : ''}</span>
			{/snippet}
			{#snippet actions()}
				{#if acts && picked.size}
					<span data-testid="review-picked">{picked.size} selected</span>
					<button class="btn primary" disabled={!!busy} onclick={() => void accept([...picked], '*')} data-testid="review-accept-picked">{busy === '*' ? 'Accepting…' : `Accept ${picked.size}`}</button>
					<button class="btn quiet" onclick={() => (picked = new Set())} data-testid="review-clear">Clear</button>
				{/if}
			{/snippet}
		</ActionBar>
		{#if !reviewer}<p class="muted" data-testid="review-no-reviewer">Choose your reviewer name in Settings to accept.</p>
		{:else if !served}<p class="muted" data-testid="review-read-only">This copy of the quilt only reads; accepting needs the quilt served for writing.</p>{/if}
		{#if !waiting}<Empty text={`Every block of ${file} is accepted.`} testid="review-empty" />{/if}
		{#if groups.changed.length}{@render group('changed', 'Changed since you accepted', groups.changed, true)}{/if}
		{#each groups.taken as t (t.label)}{@render group('taken', t.label, t.rows, false)}{/each}
		{#if groups.never.length}{@render group('never', 'Never accepted', groups.never, false)}{/if}
		{#if groups.accepted.length}
			<details class="group" data-testid="review-group" data-group="accepted">
				<summary><span class="title">Accepted</span> <span class="count" data-testid="review-group-count">{groups.accepted.length}</span></summary>
				<ul>
					{#each groups.accepted as k (k.key)}
						<li class="block" id={`review-${anchorId(k.key)}`} data-testid="review-row" data-key={k.key}>
							<div class="line">
								<a class="name" href={readUrl(doc.path, k.key)}>{name(k.key)}</a>
								<Badge parts={reviewRowBadge(m, k)} />
								{#if k.acceptance}<span class="why">by {k.acceptance.author}, {shortDate(k.acceptance.date)}</span>{/if}
							</div>
						</li>
					{/each}
				</ul>
			</details>
		{/if}
	{/if}
</main>

<style>
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
		gap: 10px;
		flex-wrap: wrap;
	}
	.line input {
		align-self: center;
	}
	.name {
		font-size: 14px;
		overflow-wrap: anywhere;
	}
	.why,
	.note {
		font-size: 12.5px;
		color: var(--ink-soft);
	}
	.acts {
		margin-left: auto;
		display: flex;
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
	select {
		max-width: 100%;
	}
</style>
