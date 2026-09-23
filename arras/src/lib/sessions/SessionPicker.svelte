<script lang="ts">
	// The session picker (plan 0.13.3 S7): what the side panel's footer opens. A session is somewhere you go rather than something kept open, so the list lives here and the panel carries only the write target (DR-229-ikmartin).
	//
	// **One selection, and it is where writes land.** Open and closed sessions share it: there is a selected session, or none, and `select none` is the only way to have none.
	//
	// **The find field narrows this list; nothing else does.** Which sessions' annotations a page draws is the filter's business, in the rail above the content.
	import { store } from '$lib/manifest/client.svelte';
	import { grouped, sessionView, summary, titleOf } from './sessions.svelte';
	import { touched, when } from './when';
	import { openSession } from './new';
	import { openDiscussion } from '$lib/workspace/links';
	import { write } from '$lib/write';
	import type { SessionRow } from '$lib/manifest/types';

	let { onpicked, ondelete }: { onpicked: () => void; ondelete: (s: SessionRow) => void } = $props();

	const m = $derived(store.manifest);
	let find = $state('');
	const groups = $derived.by(() => {
		const all = grouped(m);
		const q = find.trim().toLowerCase();
		const hit = (s: SessionRow) => !q || `${titleOf(s)} ${s.purpose ?? ''}`.toLowerCase().includes(q);
		return { open: all.open.filter(hit), closed: all.closed.filter(hit), closedCount: all.closed.length };
	});

	let naming = $state(false);
	let newName = $state('');
	let busy = $state('');
	let renaming = $state('');
	let title = $state('');
	let closedOpen = $state(false);

	async function start(): Promise<void> {
		const want = newName.trim();
		naming = false;
		newName = '';
		if (!want) return;
		const id = await openSession(want);
		if (id) {
			openDiscussion(id);
			onpicked();
		}
	}

	async function act(id: string, endpoint: string, body: Record<string, unknown> = {}): Promise<boolean> {
		busy = id;
		const res = await write(endpoint, { session: id, ...body });
		busy = '';
		store.refresh();
		return res.ok;
	}

	async function rename(s: SessionRow): Promise<void> {
		const want = title.trim();
		renaming = '';
		if (!want || want === titleOf(s)) return;
		// shown at once; the footer drops the pending name when the manifest catches up
		sessionView.renamed[s.id] = want;
		if (!(await act(s.id, 'session-rename', { title: want }))) delete sessionView.renamed[s.id];
	}

	function choose(s: SessionRow): void {
		sessionView.select(s.id, m);
		openDiscussion(s.id);
		onpicked();
	}

	async function shut(id: string): Promise<void> {
		if (await act(id, 'session-close')) sessionView.dropped(id);
	}

	/** Reopen and select (S8): the refusal's wording promises this path, and a reopened session nobody selected would still refuse. */
	async function reopen(s: SessionRow): Promise<void> {
		if (!(await act(s.id, 'session-reopen'))) return;
		// set directly rather than through `select`: the manifest still says closed, and that would admit every closed session's annotations
		sessionView.selected = s.id;
		sessionView.save();
		openDiscussion(s.id);
		onpicked();
	}

	function closedShown(yes: boolean): void {
		sessionView.showClosed = yes;
		sessionView.save();
	}

	/** Everything a row does not draw, for the pointer that lingers on it. */
	function about(s: SessionRow): string {
		const it = summary(m, s.id);
		return [s.purpose, it.who.join(', '), touched(s.opened || s.created, s.state), ...(s.attached ?? []).map((a) => `${a.who} (${a.kind}) attached`)]
			.filter(Boolean)
			.join(' · ');
	}
</script>

<div class="picker" data-testid="session-picker">
	<div class="top">
		{#if naming}
			<!-- svelte-ignore a11y_autofocus -->
			<input
				class="field"
				bind:value={newName}
				placeholder="what this sitting is for"
				aria-label="The new session's title"
				data-testid="session-new-title"
				autofocus
				onkeydown={(e) => (e.key === 'Enter' ? start() : e.key === 'Escape' ? ((naming = false), e.stopPropagation()) : undefined)}
			/>
		{:else}
			<input class="field" type="search" bind:value={find} placeholder="find a session" aria-label="Find a session" data-testid="session-find" />
			<button type="button" class="new" title="Start a new session" data-testid="session-new" onclick={() => (naming = true)}>+ new</button>
		{/if}
	</div>

	{#snippet row(s: SessionRow)}
		{@const it = summary(m, s.id)}
		{@const mine = sessionView.selected === s.id}
		{@const shutAlready = s.state !== 'open'}
		<li class:selected={mine} class:shut={shutAlready} title={about(s)}>
			{#if renaming === s.id}
				<!-- svelte-ignore a11y_autofocus -->
				<input
					class="rename"
					bind:value={title}
					aria-label="Rename {titleOf(s)}"
					data-testid="session-rename-{s.id}"
					autofocus
					onkeydown={(e) => (e.key === 'Enter' ? rename(s) : e.key === 'Escape' ? ((renaming = ''), e.stopPropagation()) : undefined)}
					onblur={() => rename(s)}
				/>
			{:else}
				<button type="button" class="pick" aria-pressed={mine} data-testid="session-{s.id}" onclick={() => choose(s)}>
					<span class="dot" aria-hidden="true"></span>
					<span class="title">{titleOf(s)}</span>
					{#each s.attached ?? [] as a (a.who)}<span class="attached" data-testid="attached-{a.who}">{a.who}</span>{/each}
					{#if !shutAlready}<span class="count">{it.open ? `${it.open} open` : 'nothing open'}</span>{/if}
					<span class="when">{when(s.opened || s.created)}</span>
				</button>
				{#if shutAlready}
					<button type="button" class="reopen" title="Reopen and select" aria-label="Reopen {titleOf(s)}" disabled={busy === s.id} data-testid="session-reopen-{s.id}" onclick={() => reopen(s)}>⟳</button>
				{/if}
				<!-- Over the row's end rather than beside it, on hover or keyboard focus only, so a row does not grow or shift when they appear and at rest it reads as the mockup does (the tab rule, W4). -->
				<span class="verbs">
					<button
						type="button"
						title="Rename"
						aria-label="Rename {titleOf(s)}"
						disabled={busy === s.id}
						data-testid="session-edit-{s.id}"
						onclick={() => {
							renaming = s.id;
							title = titleOf(s);
						}}>✎</button
					>
					{#if !shutAlready}
						<button type="button" title="Close this session" aria-label="Close {titleOf(s)}" disabled={busy === s.id} data-testid="session-close-{s.id}" onclick={() => shut(s.id)}>⏹</button>
					{/if}
					<button type="button" title="Remove from view" aria-label="Remove {titleOf(s)}" disabled={busy === s.id} data-testid="session-delete-{s.id}" onclick={() => ondelete(s)}>✕</button>
				</span>
			{/if}
		</li>
	{/snippet}

	<p class="band">Writing into</p>
	<ul class="rows" data-testid="session-list">
		{#each groups.open as s (s.id)}{@render row(s)}{:else}
			<li class="none">{find.trim() ? 'nothing matches' : 'no open sessions'}</li>
		{/each}
	</ul>

	{#if groups.closedCount}
		<p class="band rule">
			<button type="button" class="fold" aria-expanded={closedOpen} data-testid="show-closed" onclick={() => (closedOpen = !closedOpen)}>
				Closed ({groups.closedCount}) <span class="chev" class:down={closedOpen} aria-hidden="true"></span>
			</button>
		</p>
		{#if closedOpen}
			<p class="setting">
				<span>show their annotations</span>
				<span class="choice" role="group" aria-label="display closed sessions">
					<button type="button" class:on={!sessionView.showClosed} data-testid="closed-no" onclick={() => closedShown(false)}>no</button
					><button type="button" class:on={sessionView.showClosed} data-testid="closed-yes" onclick={() => closedShown(true)}>yes</button>
				</span>
			</p>
			<ul class="rows" data-testid="closed-list">
				{#each groups.closed as s (s.id)}{@render row(s)}{/each}
			</ul>
		{/if}
	{/if}

	<p class="none-row rule">
		<button
			type="button"
			class="as-link"
			disabled={!sessionView.selected}
			data-testid="session-none"
			onclick={() => {
				sessionView.clear();
				onpicked();
			}}>select none</button
		>
	</p>
</div>

<style>
	.picker {
		font-family: var(--sans);
		font-size: 12px;
		padding: var(--gap-tight);
	}
	.top {
		display: flex;
		gap: var(--gap-tight);
		margin-bottom: var(--gap-tight);
	}
	.field,
	.rename {
		flex: 1 1 auto;
		min-width: 0;
		font: inherit;
		padding: 3px 8px;
		border: 1px solid transparent;
		border-radius: var(--rad-pill);
		background: var(--leaf);
		color: var(--ink);
	}
	.field:focus,
	.rename:focus {
		border-color: var(--rule-strong);
		outline: none;
	}
	.new {
		flex: none;
		font: inherit;
		color: var(--ink-soft);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 2px 8px;
		cursor: pointer;
	}
	.new:hover {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
	.band {
		margin: var(--gap-tight) 0 var(--gap-hair);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
	}
	.rule {
		border-top: 1px solid var(--rule);
		padding-top: var(--gap-tight);
	}
	ul.rows {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		--row: var(--sheet);
		position: relative;
		display: flex;
		align-items: center;
		border-radius: var(--rad-pill);
		background: var(--row);
	}
	li:hover {
		--row: var(--paper);
	}
	li.selected {
		--row: var(--leaf);
	}
	li.none {
		padding: 4px 8px;
		color: var(--ink-faint);
	}
	.pick {
		flex: 1 1 auto;
		min-width: 0;
		display: flex;
		align-items: baseline;
		gap: 8px;
		font: inherit;
		color: var(--ink);
		background: none;
		border: 0;
		padding: 5px 8px;
		text-align: left;
		cursor: pointer;
	}
	.dot {
		flex: none;
		align-self: center;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--link);
	}
	li.shut .dot {
		background: none;
		box-shadow: inset 0 0 0 1.5px var(--ink-faint);
	}
	.title {
		flex: 1 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	li.selected .title {
		font-weight: 600;
	}
	li.shut .title {
		color: var(--ink-soft);
	}
	.attached {
		flex: none;
		font-size: 10px;
		color: var(--link);
	}
	.attached::before {
		content: '⟨';
	}
	.attached::after {
		content: '⟩';
	}
	.count,
	.when {
		flex: none;
		color: var(--ink-faint);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.reopen {
		flex: none;
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		padding: 0 8px 0 0;
		cursor: pointer;
	}
	.verbs {
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		display: none;
		align-items: center;
		gap: 2px;
		padding: 0 6px 0 22px;
		border-radius: 0 var(--rad-pill) var(--rad-pill) 0;
		background: linear-gradient(to right, transparent, var(--row) 18px);
	}
	li:hover .verbs,
	li:focus-within .verbs {
		display: flex;
	}
	/* ⟳ is always drawn on a closed row (S7), so the verbs stop short of it rather than covering it */
	li.shut .verbs {
		right: 1.6em;
		border-radius: 0;
	}
	.verbs button {
		font: inherit;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 0 3px;
		cursor: pointer;
	}
	.verbs button:hover {
		color: var(--ink);
	}
	.fold {
		display: flex;
		align-items: center;
		gap: var(--gap-hair);
		font: inherit;
		text-transform: inherit;
		letter-spacing: inherit;
		color: inherit;
		background: none;
		border: 0;
		padding: 0;
		cursor: pointer;
	}
	.fold:hover {
		color: var(--ink-soft);
	}
	.chev {
		width: 5px;
		height: 5px;
		border-right: 1.5px solid currentColor;
		border-bottom: 1.5px solid currentColor;
		transform: rotate(-45deg);
		margin-bottom: 1px;
	}
	.chev.down {
		transform: rotate(45deg);
		margin-bottom: 3px;
	}
	.setting {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 0 0 var(--gap-hair) 8px;
		color: var(--ink-faint);
		font-size: 11px;
	}
	.choice {
		display: inline-flex;
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		overflow: hidden;
	}
	.choice button {
		font: inherit;
		color: var(--ink-soft);
		background: var(--leaf);
		border: 0;
		padding: 0 7px;
		cursor: pointer;
	}
	.choice button + button {
		border-left: 1px solid var(--rule);
	}
	.choice button.on {
		background: var(--link-wash);
		color: var(--link);
	}
	.none-row {
		margin: var(--gap-tight) 0 0;
		padding-left: 8px;
	}
	.none-row button {
		font: inherit;
		color: var(--ink-soft);
	}
	.none-row button:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
</style>
