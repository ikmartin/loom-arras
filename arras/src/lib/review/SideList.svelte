<script lang="ts">
	// The list beside a text. **Comments**: every annotation and pending change here in reading order, a card each, which opens it at its mark: an annotation's with its colour, author, quoted words and comment (a PDF's mark not found again on the changed file says so, having none), a change's with its words out and in and Keep and Discard (`ChangeCard`). Where the text has changes, All, Annotations and Changes choose what is listed, and with annotations alone the text shows what the person has kept. To do keeps the changes and the open annotations of types that stay open, from others than the reader; the filter leaves out people, an edit made in the file being its own, and shows or hides the resolved. **Notes**: every annotation whose type is listed in Notes, from every document and work, grouped by document, each a link back to where it was left. Both are built from the manifest; nobody edits them.
	import Icon from '$lib/components/Icon.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import type { Annotation } from '$lib/manifest/types';
	import { repliesTo } from '$lib/annotations';
	import { ui } from '$lib/ui.svelte';
	import { staysOpen, typeOf } from './annotationTypes';
	import { authors, changePasses, entries, isTodo, notesIn, placeOf, plain, type Annotating, type Layer } from './annotating.svelte';
	import { authorOf, changeById } from './changes';
	import { dotVars } from '$lib/fragments/gutter';
	import ChangeCard from './ChangeCard.svelte';

	let { notes }: { notes: Annotating } = $props();

	const m = $derived(store.manifest);
	const seq = $derived(entries(m, notes));
	/** Everyone who wrote here, whether the filter shows them or not. */
	const all = $derived(m ? notes.order.map((id) => m.annotations[id]).filter((a): a is Annotation => !!a) : []);
	const changes = $derived(m ? notes.order.map((id) => changeById(m, id)).filter((c) => !!c) : []);
	const people = $derived.by(() => {
		const out = authors(m, all);
		for (const c of changes) if (!out.some((p) => p.id === authorOf(c!).id)) out.push(authorOf(c!));
		return out;
	});
	const todo = $derived(all.filter((a) => isTodo(m, a) && !notes.hidden.includes(a.author.id)).length + changes.filter((c) => changePasses(c!, { hidden: notes.hidden, layer: 'all' })).length);
	const filtered = $derived(notes.hidden.length > 0 || notes.layer !== 'all');
	const LAYERS: [Layer, string][] = [
		['all', 'All'],
		['annotations', 'Annotations'],
		['changes', 'Changes']
	];
	const groups = $derived(notesIn(m));

	let filtering = $state(false);
	let list = $state<HTMLElement | null>(null);

	// the open annotation's card is kept in view
	$effect(() => {
		void notes.open;
		list?.querySelector('.card.on')?.scrollIntoView({ block: 'nearest' });
	});

	function who(id: string, shown: boolean): void {
		notes.hidden = shown ? notes.hidden.filter((x) => x !== id) : [...notes.hidden, id];
	}

	function open(id: string): void {
		if (!notes.show(id)) notes.open = id;
	}

	const typeLine = (a: Annotation) => [typeOf(m, a)?.name, shortDate(a.created)].filter(Boolean).join(' · ');
</script>

<aside class="side" aria-label={notes.side === 'notes' ? 'Notes' : changes.length ? 'Comments and changes' : 'Comments'} data-testid="side-list" data-pane-side={notes.side}>
	{#if notes.side === 'notes'}
		<div class="shead">
			<div class="row"><span class="stitle">Notes</span><button type="button" class="x" aria-label="Close notes" title="Close notes" data-testid="side-close" onclick={() => (notes.side = null)}><Icon name="close" size={14} /></button></div>
			<p class="nsub">Every annotation whose type is listed in Notes, from every document, each linked back to where it was left.</p>
		</div>
		<div class="cards" bind:this={list}>
			{#each groups as g (g.label)}
				<div class="ngroup" data-testid="notes-group">{g.label}<span class="badge">{g.notes.length}</span></div>
				{#each g.notes as a (a.id)}
					<a class="card ncard" class:on={notes.open === a.id} href="quilt:{a.id}" data-testid="note-card" data-annotation={a.id}>
						<div class="ch"><span class="dot2" style={dotVars(a)}></span><span class="who">{a.author.label ?? a.author.id}</span><span>{typeLine(a)}</span></div>
						{#if a.quote}<div class="q"><TexProse text={a.quote} /></div>{/if}
						{#if plain(a.body_html)}<div class="ct"><Prose html={a.body_html} /></div>{:else}<div class="ct none">No comment</div>{/if}
						<div class="nfoot"><span>{m ? placeOf(m, a) : ''}</span><span class="go">Go to it →</span></div>
					</a>
				{/each}
			{:else}
				<div class="sempty">No notes yet. Annotate with a type listed in Notes.</div>
			{/each}
		</div>
	{:else}
		<div class="shead">
			<div class="row">
				<span class="stitle">{changes.length ? 'Comments and changes' : 'Comments'}</span>
				<button type="button" class="tool" class:on={filtering || filtered} aria-expanded={filtering} title="Filter by person and resolved" data-testid="comments-filter" onclick={() => (filtering = !filtering)}><Icon name="filter" size={13} />Filter</button>
				<button type="button" class="x" aria-label="Close the list" title="Close the list" data-testid="side-close" onclick={() => (notes.side = null)}><Icon name="close" size={14} /></button>
			</div>
			<div class="row">
				{#if changes.length}
					<div class="seg" role="group" aria-label="Which to list">
						{#each LAYERS as [l, name] (l)}<button type="button" class:on={notes.layer === l} aria-pressed={notes.layer === l} data-testid="layer-{l}" onclick={() => (notes.layer = l)}>{name}</button>{/each}
					</div>
				{/if}
				<button type="button" class="tool todo" class:on={notes.todo} aria-pressed={notes.todo} title={changes.length ? 'To do: changes to keep or discard, and open annotations from others' : 'To do: open annotations from others'} data-testid="comments-todo" onclick={() => (notes.todo = !notes.todo)}>To do<span class="badge">{todo}</span></button>
			</div>
			{#if filtering}
				<div class="fmenu" data-testid="filter-menu">
					<div class="sec">Whose</div>
					{#each people as p (p.id)}
						<label class="chk"><input type="checkbox" checked={!notes.hidden.includes(p.id)} data-testid="filter-who" data-author={p.id} onchange={(e) => who(p.id, e.currentTarget.checked)} />{p.id === m?.reviewer?.name ? `${p.name} (you)` : p.name}</label>
					{/each}
					<label class="chk resolved"><input type="checkbox" checked={ui.showSettled} data-testid="filter-resolved" onchange={(e) => (ui.showSettled = e.currentTarget.checked)} />Resolved annotations</label>
				</div>
			{/if}
		</div>
		<div class="cards" bind:this={list}>
			{#each seq as e (e.id)}
				{#if e.c}
					<ChangeCard c={e.c} on={notes.open === e.id} onopen={() => open(e.id)} />
				{:else}
				{@const a = e.a}
				{@const replies = m ? repliesTo(m, a.id).length : 0}
				<div class="card" class:on={notes.open === a.id} class:settled={a.status !== 'open'} role="button" tabindex="0" data-testid="comment-card" data-annotation={a.id} onclick={() => open(a.id)} onkeydown={(e) => e.key === 'Enter' && open(a.id)}>
					<div class="ch"><span class="dot2" style={dotVars(a)}></span><span class="who">{a.author.label ?? a.author.id}</span><span>{typeLine(a)}</span></div>
					{#if a.quote}<div class="q"><TexProse text={a.quote} /></div>{/if}
					{#if plain(a.body_html)}<div class="ct"><Prose html={a.body_html} /></div>{:else}<div class="ct none">No comment</div>{/if}
					{#if a.detached && a.target.page}<div class="ct none" data-testid="card-detached">Not found again on the changed PDF, so drawn on no page.</div>{/if}
					{#if staysOpen(m, a) || replies}
						<div class="cf">
							{#if staysOpen(m, a)}<span class="stat" class:done={a.status !== 'open'}>{a.status === 'open' ? 'Open' : 'Resolved'}</span>{/if}
							{#if replies}<span class="none">{replies} {replies === 1 ? 'reply' : 'replies'}</span>{/if}
						</div>
					{/if}
				</div>
				{/if}
			{:else}
				<div class="sempty">{notes.todo && !filtered ? 'Nothing to do.' : filtered || notes.todo ? 'Nothing matches the filter.' : changes.length ? 'No comments or changes.' : 'No comments.'}</div>
			{/each}
		</div>
	{/if}
</aside>

<style>
	.side {
		display: flex;
		flex-direction: column;
		box-sizing: border-box;
		width: 310px;
		height: 100%;
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink);
		background: var(--sheet);
		border-left: 1px solid var(--rule);
	}
	.shead {
		position: relative;
		display: grid;
		gap: 6px;
		padding: 10px 12px 8px;
		border-bottom: 1px solid var(--rule);
	}
	.row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.stitle {
		flex: 1;
		font-weight: 600;
	}
	.nsub {
		margin: 0;
		color: var(--ink-soft);
		line-height: 1.4;
	}
	.x,
	.tool {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		height: 24px;
		padding: 0 7px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		border-radius: 5px;
		cursor: pointer;
	}
	.x {
		width: 24px;
		padding: 0;
		justify-content: center;
	}
	.x:hover,
	.tool:hover {
		color: var(--ink);
		background: var(--leaf);
	}
	.tool.on {
		color: var(--ink);
		background: var(--accent-wash);
	}
	.tool.todo {
		border: 1px solid var(--rule);
	}
	.seg {
		display: inline-flex;
		flex: 1;
		border: 1px solid var(--rule);
		border-radius: 6px;
		overflow: hidden;
	}
	.seg button {
		flex: 1;
		height: 24px;
		padding: 0 6px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.seg button + button {
		border-left: 1px solid var(--rule);
	}
	.seg button.on {
		color: var(--ink);
		background: var(--accent-wash);
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
	.fmenu {
		display: grid;
		gap: 4px;
		padding: 8px 10px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 6px;
	}
	.sec {
		font-size: 10.5px;
		font-weight: 600;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	.chk {
		display: flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
	}
	.chk.resolved {
		margin-top: 6px;
	}
	.cards {
		flex: 1;
		display: grid;
		align-content: start;
		gap: 8px;
		padding: 10px 12px;
		overflow-y: auto;
	}
	.card {
		display: grid;
		gap: 4px;
		padding: 8px 10px;
		color: inherit;
		text-decoration: none;
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 8px;
		cursor: pointer;
	}
	.card:hover {
		border-color: var(--rule-strong);
	}
	.card.on {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.card.settled {
		opacity: 0.55;
	}
	.ch {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		font-size: 11.5px;
		color: var(--ink-faint);
	}
	.dot2 {
		flex: none;
		width: 10px;
		height: 10px;
		box-sizing: border-box;
		border-radius: 50%;
		background: var(--fill);
		border: 1.5px solid var(--edge);
	}
	.who {
		font-weight: 600;
		color: var(--ink-soft);
	}
	.q {
		display: block;
		padding-left: 8px;
		font-family: var(--body-face);
		font-size: 13px;
		line-height: 1.4;
		color: var(--ink-soft);
		border-left: 2px solid var(--rule);
		overflow: hidden;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
	}
	.ct {
		display: block;
		font-family: var(--body-face);
		font-size: 13px;
		line-height: 1.4;
	}
	.ct :global(p) {
		margin: 0.15em 0;
	}
	.none {
		color: var(--ink-faint);
		font-family: var(--sans);
		font-size: 12px;
	}
	.cf,
	.nfoot {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 11.5px;
		color: var(--ink-faint);
	}
	.nfoot {
		justify-content: space-between;
	}
	.go {
		color: var(--link);
	}
	.stat {
		padding: 0 6px;
		font-size: 10.5px;
		font-weight: 600;
		color: var(--accent);
		border: 1px solid var(--accent);
		border-radius: 9px;
	}
	.stat.done {
		color: var(--ink-faint);
		border-color: var(--rule-strong);
	}
	.ngroup {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 4px;
		font-size: 11px;
		font-weight: 600;
		color: var(--ink-soft);
	}
	.sempty {
		padding: 16px 4px;
		color: var(--ink-faint);
		text-align: center;
	}
</style>
