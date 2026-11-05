<script lang="ts">
	// The left column: the quilt's name, the fold and Settings at its head; two tabs choosing the primary view, **Docs** (reading and writing) and **Review** (the quilt's management); beneath them that view's column; and a footer, in both views, holding the session footer. Folded, it is a narrow rail keeping what must stay in reach: unfold and the session's dot. Search is ⌘K alone; what is wrong is Review › Problems, which counts it.
	//
	// **Docs** holds a page's own panel where it registers one (the graph's filters), else the project's tree under Files (`FileTree`: its directories and the files the viewer shows, each agent copy beneath the document it copies), a shelf open by default and folding as Library's does, a copy whose document is not listed under Agent documents with the closed ones folded beneath, the Library, folded until opened — and beneath them, past a line the reader drags up and down, the Outline of the document in the focused pane. The two scroll apart. A result is read in the document that holds it (V7), so the column lists no nodes. A publisher that lists no files gets the documents alone, as before.
	import Contents from './Contents.svelte';
	import FileTree from './FileTree.svelte';
	import AgentMark from './AgentMark.svelte';
	import { explain, says } from './access';
	import AddWork from '$lib/components/AddWork.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { isAgentDocument } from '$lib/manifest/documents';
	import { documentLabel } from '$lib/workspace/names';
	import { masterUrl, workUrl } from '$lib/nav';
	import { shelf } from '$lib/library';
	import SessionFooter from '$lib/sessions/SessionFooter.svelte';
	import { onMount } from 'svelte';
	import { can } from '$lib/write';
	import Settings from './Settings.svelte';
	import { COLUMN_MAX, COLUMN_MIN, prefs } from '$lib/prefs.svelte';
	import { route } from '$lib/paths';
	import type { ShellProps } from './props';
	import type { Master } from '$lib/manifest/types';
	import { page } from '$app/state';
	import { needsYou } from '$lib/library';
	import { reviewLanding, sectionOf, sectionsOf } from '$lib/review/sections';

	let { label, primary, docsHref, indexes, masters, currentDoc, onDocument, contents, currentSection, children, rail, panel, panelLabel }: ShellProps = $props();

	// The Library in the column: a work is one thing a reader opens, so the column lists them, one row each however many documents it has. A row carries the work's title alone: what each holds and needs is said on its Info and on the library's page, not beside every row. A choice opens in the focused pane, as every choice in the column does.
	const works = $derived(store.manifest ? shelf(store.manifest) : []);
	let readOnly = $state(false);
	onMount(() => { void can('review-accept').then((yes) => readOnly = !yes); });
	const reviewPerspective = $derived(store.manifest?.reviewer?.name
		? `Review status for ${store.manifest.reviewer.name}`
		: Object.values(store.manifest?.keys ?? {}).some((key) => key.acceptance) ? 'Review perspective unspecified' : '');
	let workFilter = $state('');
	const library = $derived.by(() => {
		const q = workFilter.trim().toLowerCase();
		return q ? works.filter((r) => r.text.includes(q)) : works;
	});

	// **On a narrow window the column goes first** (plan 0.13 §7): below 1200px the workspace needs the width, so the column shows folded whatever the reader's stored choice, and the fold opens it for this visit without rewriting that choice. A window widened again shows the stored choice.
	const SQUEEZED = 1200;
	let windowWidth = $state(typeof window === 'undefined' ? SQUEEZED : window.innerWidth);
	let peek = $state<boolean | null>(null);
	const squeezed = $derived(windowWidth < SQUEEZED);
	const shown = $derived(squeezed ? (peek ?? false) : prefs.panel);
	$effect(() => {
		if (!squeezed) peek = null;
	});
	function fold(): void {
		if (squeezed) peek = !shown;
		else prefs.panel = !prefs.panel;
	}

	// Documents: the drafts being worked on, as a list rather than a dropdown, because a dropdown shows one name at a time and cannot say which draft is conflicted. A landmark is reached from its draft's history and from Review › History, not listed here.
	const own = $derived(masters.filter((m) => !m.closed && !m.context_only && !isAgentDocument(m)));
	const withAgent = $derived(masters.filter((m) => !m.closed && !m.context_only && isAgentDocument(m)));
	const closed = $derived(masters.filter((m) => m.closed));
	// an agent's copy is read beside the document it copies, so it sits beneath that document's row; one whose document is not listed (closed, context-only, gone) stands on its own after them
	const copiesOf = (path: string) => withAgent.filter((m) => m.copy_of === path);
	// a copy is one agents edit, said where the publisher says who edits its files at all
	const marks = $derived(says(store.manifest?.files));
	const unplaced = $derived(withAgent.filter((m) => !own.some((o) => o.path === m.copy_of)));
	// a copy of one section says which, since several sections of one document may each have a copy
	const section = (m: Master) => (m.scope?.kind === 'section' ? m.scope.title ?? m.scope.key ?? '' : '');
	// The file name, not the typeset title: two drafts of one paper share a title and differ only in their path, which is what the author types and what the read view's URL names them by; the path itself where two files share a name.
	const filename = (path: string) => documentLabel(masters, path);
	const outline = $derived(onDocument && contents.length > 0);
	// Review's sections, each with what waits for the author there
	const sections = $derived(store.manifest ? sectionsOf(store.manifest) : []);
	const here = $derived(sectionOf(page.route.id));
	// the works wanting something of the person beyond results to check, which Review's Proposed Changes counts
	const wanted = $derived(store.manifest ? needsYou(store.manifest) : 0);

	// folded until the reader opens it: the works are many, and the documents are what the column is for
	let libraryOpen = $state(false);
	// the project's files, open until the reader folds them
	let filesOpen = $state(true);
	// adding a work by hand, where the publisher writes the library
	let canAdd = $state(false);
	let adding = $state(false);
	onMount(() => {
		void can('library-add').then((yes) => (canAdd = yes));
	});

	// The line between the documents and the outline: where it stands is a preference, drawn at most once a frame while it is dragged and stored at the drop, as the pane divider is.
	const STEP = 0.03;
	let sectionsBox = $state<HTMLElement | null>(null);
	let live = $state<number | null>(null);
	let box: DOMRect | null = null;
	let next: number | null = null;
	let painting = 0;
	const clamp = (v: number) => Math.min(0.85, Math.max(0.15, v));
	const share = $derived(live ?? prefs.outline);
	function grab(e: PointerEvent): void {
		if (!sectionsBox) return;
		// the press's default would start a text selection, or a native drag of a link the line passes, which takes the pointer away mid-drag
		e.preventDefault();
		box = sectionsBox.getBoundingClientRect();
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		drag(e);
	}
	function drag(e: PointerEvent): void {
		if (!box) return;
		next = clamp((e.clientY - box.top) / (box.height || 1));
		painting ||= requestAnimationFrame(() => {
			painting = 0;
			live = next;
		});
	}
	function drop(e: PointerEvent): void {
		if (!box) return;
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
		cancelAnimationFrame(painting);
		painting = 0;
		if (next !== null) prefs.outline = next;
		live = next = box = null;
	}
	function nudge(e: KeyboardEvent): void {
		if (e.key === 'ArrowUp') prefs.outline = clamp(prefs.outline - STEP);
		else if (e.key === 'ArrowDown') prefs.outline = clamp(prefs.outline + STEP);
		else return;
		e.preventDefault();
	}

	// The line between the column and the panes moves as the outline's does, sideways: the column's width is a preference, drawn at most once a frame while it is dragged and stored at the drop.
	const WIDEN = 16;
	let panelBox = $state<HTMLElement | null>(null);
	let liveWidth = $state<number | null>(null);
	let left: number | null = null;
	let nextWidth: number | null = null;
	let sizing = 0;
	const fit = (v: number) => Math.round(Math.min(COLUMN_MAX, Math.max(COLUMN_MIN, v)));
	const width = $derived(liveWidth ?? prefs.column);
	function grabEdge(e: PointerEvent): void {
		if (!panelBox) return;
		e.preventDefault();
		left = panelBox.getBoundingClientRect().left;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		dragEdge(e);
	}
	function dragEdge(e: PointerEvent): void {
		if (left === null) return;
		nextWidth = fit(e.clientX - left);
		sizing ||= requestAnimationFrame(() => {
			sizing = 0;
			liveWidth = nextWidth;
		});
	}
	function dropEdge(e: PointerEvent): void {
		if (left === null) return;
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
		cancelAnimationFrame(sizing);
		sizing = 0;
		if (nextWidth !== null) prefs.column = nextWidth;
		liveWidth = nextWidth = left = null;
	}
	function nudgeEdge(e: KeyboardEvent): void {
		if (e.key === 'ArrowLeft') prefs.column = fit(prefs.column - WIDEN);
		else if (e.key === 'ArrowRight') prefs.column = fit(prefs.column + WIDEN);
		else return;
		e.preventDefault();
	}
</script>

<svelte:window bind:innerWidth={windowWidth} />

<div class="shell-c" style:--column-width="{width}px">
	<div class="panel" class:away={!shown} data-testid="column" bind:this={panelBox}>
		{#if !shown}
			<!-- folded: what must stay in reach, one above the other -->
			<button class="fold" title="Show the column" aria-label="Show the column" aria-expanded="false" data-testid="panel-fold" onclick={fold}>»</button>
			<div class="rail-foot">
				<SessionFooter compact />
			</div>
		{:else}
			<div class="head">
				<a href={route('/')} class="name" data-testid="quilt-name">{label}</a>
				<Settings {indexes} />
				<button class="fold" title="Hide the column" aria-label="Hide the column" aria-expanded="true" data-testid="panel-fold" onclick={fold}>«</button>
			</div>
			<nav class="primary" aria-label="Primary views">
				<!-- back to Docs returns to the workspace's address, which names the place a link last sent a tab to; each pane puts the reader back where they were, so neither scrolling nor focus is let go to that place first -->
				<a
					href={docsHref || route('/')}
					class:on={primary === 'docs'}
					aria-current={primary === 'docs' ? 'page' : undefined}
					data-sveltekit-noscroll=""
					data-sveltekit-keepfocus=""
					data-testid="primary-docs">Docs</a
				>
				<!-- a corpus that declares no review has no Review; one that says nothing either way keeps it -->
				{#if store.manifest?.publishes?.review !== false}<a href={reviewLanding(sections)} class:on={primary === 'review'} aria-current={primary === 'review' ? 'page' : undefined} data-testid="primary-review">Review</a>{/if}
			</nav>
			<!-- Whose review a read-only view shows is said once, under the quilt it belongs to, and never above the document. -->
			{#if readOnly && reviewPerspective}<p class="review-perspective">{reviewPerspective}</p>{/if}
			<div class="sections" bind:this={sectionsBox}>
				{#if primary === 'review'}
					<!-- the quilt's management, one section at a time, each saying what waits there -->
					<ul class="plain review-sections" data-testid="review-sections">
						{#each sections as x (x.id)}
							<li>
								<a href={x.href} class:here={here === x.id} aria-current={here === x.id ? 'page' : undefined} title={x.says} data-testid="section-{x.id}"
									><span class="section-name">{x.label}<span class="blurb">{x.blurb}</span></span>{#if x.waits}<span class="waits" data-testid="section-count-{x.id}">{x.waits}</span>{/if}</a
								>
							</li>
						{/each}
					</ul>
				{/if}
				{#if panel}
					<p class="rail-label">{panelLabel}</p>
					<div class="page-panel rail-scroll">{@render panel()}</div>
				{:else if primary === 'docs'}
					<div class="part docs-part rail-scroll" data-testid="docs-part" style:flex={outline ? `0 0 ${share * 100}%` : '1 1 auto'}>
					{#snippet link(m: Master)}
						{@const here = onDocument && m.path === currentDoc}
						<a href={masterUrl(m.path)} class:here aria-current={here ? 'page' : undefined}>{filename(m.path)}{#if section(m)}<span class="aside">{section(m)}</span>{/if}</a>
					{/snippet}
					{#if store.manifest?.files}
						<!-- Files is the quilt's directory as it is, where Library is what loom keeps of the cited works: two shelves, folding alike, so the two read as different kinds of thing -->
						<div class="shelf-box" data-testid="files-shelf">
							<p class="shelf-head">
								<button class="shelf" aria-expanded={filesOpen} title="View of files in {store.manifest.corpus.directory ?? store.manifest.corpus.name}/" data-testid="files-toggle" onclick={() => (filesOpen = !filesOpen)}>
									<span class="caret">{filesOpen ? '▾' : '▸'}</span>Files
								</button>
							</p>
							{#if filesOpen}<div class="shelf-body"><FileTree files={store.manifest.files} {masters} {own} {copiesOf} {section} /></div>{/if}
						</div>
					{:else if store.manifest?.research_state}
						<!-- the quilt's research state (plan 0.21.3): a page about the whole quilt, so above every document, and no heading of its own -->
						{@const onState = page.route.id === '/page/[id]'}
						<ul class="plain docs state" data-testid="docs-state">
							<li><a href={route('/page/state')} class:here={onState} aria-current={onState ? 'page' : undefined}>Research state</a></li>
						</ul>
					{/if}
					{#if own.length && !store.manifest?.files}
						<p class="rail-label">Documents</p>
						<ul class="plain docs" data-testid="docs-drafts">
							{#each own as m (m.path)}
								{@const copies = copiesOf(m.path)}
								<li>
									{@render link(m)}
									{#if copies.length}
										<!-- the agent's copies of this document, which the person and an agent both edit -->
										<ul class="plain docs copies" data-testid="docs-copies">
											{#each copies as c (c.path)}<li>{@render link(c)}{#if marks}<AgentMark agents={true} said={explain({ agents: true }, { copyOf: m.path })} testid="access-{c.path}" />{/if}</li>{/each}
										</ul>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
					{#if unplaced.length || closed.length}
						<p class="rail-label">Agent documents</p>
						{#if unplaced.length}
							<ul class="plain docs" data-testid="docs-agent">
								{#each unplaced as m (m.path)}<li>{@render link(m)}{#if marks && m.copy_of}<AgentMark agents={true} said={explain({ agents: true }, { copyOf: m.copy_of })} testid="access-{m.path}" />{/if}</li>{/each}
							</ul>
						{/if}
						{#if closed.length}
							<details class="closed" data-testid="docs-closed">
								<summary>Closed agent documents</summary>
								<ul class="plain docs">
									{#each closed as m (m.path)}<li>{@render link(m)}</li>{/each}
								</ul>
							</details>
						{/if}
					{/if}
					{#if works.length || canAdd}
						<div class="shelf-box" data-testid="library-shelf">
							<p class="shelf-head">
								<button class="shelf" aria-expanded={libraryOpen} data-testid="library-toggle" onclick={() => (libraryOpen = !libraryOpen)}>
									<span class="caret">{libraryOpen ? '▾' : '▸'}</span>Library <span class="count">{works.length}</span>
								</button>
								{#if canAdd}<button class="shelf-add" aria-label="Add a work" title="Add a work" onclick={() => (adding = true)} data-testid="library-add">+</button>{/if}
							</p>
							{#if libraryOpen}
								<div class="shelf-body">
									<input class="filter" type="search" placeholder="narrow by title, author or key" aria-label="Narrow the works" bind:value={workFilter} data-testid="library-filter" />
									<ul class="plain library" data-testid="library-list">
										{#each library as r (r.citekey)}
											<li>
												<a href={workUrl(r.opens)} data-testid="library-work-{r.citekey}">{r.title}</a>
												{#if r.unreadable}<span class="aside">unreadable</span>{/if}
											</li>
										{:else}
											<li class="aside">nothing matches</li>
										{/each}
										<li><a href={route('/review/library')} data-testid="manage-link">Manage the library</a>{#if wanted}<a class="aside wanted" href={route('/review/library') + '?show=needs-you'} data-testid="manage-wanted">{wanted} {wanted === 1 ? 'needs' : 'need'} you</a>{/if}</li>
									</ul>
								</div>
							{/if}
						</div>
					{/if}
					</div>
					{#if outline}
						<!-- A separator that takes focus is a widget in ARIA's own terms, with the arrow keys and aria-valuenow this one has. -->
						<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
						<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
						<div
							class="outline-divider"
							class:moving={live !== null}
							role="separator"
							tabindex="0"
							aria-label="Resize the outline"
							aria-orientation="horizontal"
							aria-valuenow={Math.round(share * 100)}
							aria-valuemin={15}
							aria-valuemax={85}
							data-testid="outline-divider"
							onpointerdown={grab}
							onpointermove={drag}
							onpointerup={drop}
							onpointercancel={drop}
							onkeydown={nudge}
						></div>
						<!-- the focused pane's document's sections, beneath the documents and scrolled apart from them -->
						<div class="part outline-part rail-scroll" data-testid="outline">
							<p class="rail-label outline-label">Outline <span class="aside">{filename(currentDoc)}</span></p>
							<Contents entries={contents} masterPath={currentDoc} current={currentSection} />
						</div>
					{/if}
				{/if}
			</div>
			<!-- Pinned outside the scroll (S5), in both views: writes land in the selected session whatever is shown, so a reader must never go looking for where their work will go. -->
			<div class="write-target">
				<SessionFooter />
			</div>
			<!-- the column's edge, which the reader drags sideways as they drag the outline's line up and down -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
			<div
				class="column-divider"
				class:moving={liveWidth !== null}
				role="separator"
				tabindex="0"
				aria-label="Resize the column"
				aria-orientation="vertical"
				aria-valuenow={width}
				aria-valuemin={COLUMN_MIN}
				aria-valuemax={COLUMN_MAX}
				data-testid="column-divider"
				onpointerdown={grabEdge}
				onpointermove={dragEdge}
				onpointerup={dropEdge}
				onpointercancel={dropEdge}
				onkeydown={nudgeEdge}
			></div>
		{/if}
	</div>

	<div class="content">
		{@render children()}</div>
	{#if rail}<aside class="right rail-scroll">{@render rail()}</aside>{/if}
</div>

{#if canAdd}<AddWork bind:open={adding} />{/if}

<style>
	.review-perspective { margin: 0 0 var(--gap-tight); font-size: 11.5px; color: var(--ink-soft); overflow-wrap: anywhere; }
	.shell-c {
		display: grid;
		grid-template-columns: var(--column-width, var(--rail-left)) minmax(0, 1fr) auto;
		min-height: 100vh;
	}
	/* The column's edge is its border, drawn by the line the reader drags, with room inside it to take hold of. It stands in the column's own stacking, so the boxes the column opens float over it. */
	.panel:not(.away) {
		border-right: 0;
	}
	.column-divider {
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: 8px;
		z-index: 1;
		cursor: col-resize;
		touch-action: none;
	}
	.column-divider::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		border-right: 1px solid var(--rule);
	}
	.column-divider:hover::before,
	.column-divider.moving::before,
	.column-divider:focus-visible::before {
		border-right-color: var(--link);
	}
	.column-divider:focus-visible {
		outline: none;
	}
	/* folded, the column is a narrow rail, not a 252px empty gutter */
	.shell-c:has(.panel.away) {
		grid-template-columns: var(--rail-folded) minmax(0, 1fr) auto;
	}
	.panel {
		background: var(--leaf);
		border-right: 1px solid var(--rule);
		padding: var(--gap) 14px;
		position: sticky;
		z-index: 10;
		top: 0;
		height: 100vh;
		display: flex;
		flex-direction: column;
		gap: var(--gap-hair);
		overflow: hidden;
		z-index: 20;
	}
	.sections {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		gap: var(--gap-hair);
	}
	/* A label keeps its own height; the documents and the outline take the rest and scroll apart, and a page's own panel takes all of it. */
	.sections > *:not(.page-panel):not(.part) {
		flex: 0 0 auto;
	}
	/* folded: unfold, and at the foot the session's dot */
	.panel.away {
		align-items: center;
		padding-left: 4px;
		padding-right: 4px;
		gap: 12px;
	}
	.rail-foot {
		margin-top: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		width: 100%;
	}
	.rail-foot :global(.footer) {
		margin: 0 -4px calc(-1 * var(--gap));
		align-self: stretch;
	}
	/* the two primary views: one line of two words, the current one underlined */
	.primary {
		display: flex;
		gap: 16px;
		margin: 0 0 var(--gap-tight);
		border-bottom: 1px solid var(--rule);
		font-size: 12.5px;
	}
	.primary a {
		padding: 4px 0 6px;
		color: var(--ink-soft);
		margin-bottom: -1px;
	}
	.primary a:hover {
		color: var(--ink);
		text-decoration: none;
	}
	.primary a.on {
		color: var(--ink);
		box-shadow: inset 0 -2px 0 var(--accent);
	}
	.filter {
		width: 100%;
		box-sizing: border-box;
		font: inherit;
		font-size: 11px;
		padding: 2px 5px;
		margin: 0 0 var(--gap-hair);
		border: 1px solid var(--rule);
		border-radius: 3px;
		background: var(--sheet);
		color: var(--ink);
	}
	.fold {
		font: inherit;
		font-size: 11px;
		line-height: 1;
		color: var(--ink-faint);
		background: none;
		border: 0;
		padding: 2px 3px;
		cursor: pointer;
	}
	.fold:hover {
		color: var(--ink);
	}
	.page-panel {
		flex: 1;
		min-height: 0;
	}
	.head .name {
		font-size: 13px;
		color: var(--ink);
		font-weight: 500;
	}
	.head .name:hover {
		text-decoration: none;
	}
	.head {
		display: flex;
		align-items: center;
		gap: var(--gap-tight);
		margin-bottom: var(--gap-hair);
	}
	.head .name {
		margin-right: auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	ul.plain {
		list-style: none;
		margin: 0 0 var(--gap-tight);
		padding: 0;
	}
	ul.plain a {
		display: block;
		font-size: 11px;
		color: var(--ink-soft);
		padding: 1px 6px;
		border-radius: var(--rad-pill);
	}
	ul.plain a:hover {
		color: var(--ink);
		text-decoration: none;
	}
	.write-target {
		flex: none;
	}
	.content {
		min-width: 0;
	}
	aside.right {
		width: var(--rail-right);
		border-left: 1px solid var(--rule);
		padding: var(--gap);
		position: sticky;
		top: 0;
		max-height: 100vh;
	}
	/* A shelf is a box with rounded corners, a shade lighter than the column, holding its head and, open, its rows: Files and Library are the column's two kinds of thing, and read as sections rather than as labels. The rows start at the box's own edge, so the column's width goes to the names. */
	.shelf-box {
		margin: var(--gap-tight) 0 var(--gap-hair);
		border-radius: var(--rad-control);
		/* a wash of the ink, so the box shows on the column in either theme */
		background: color-mix(in srgb, var(--ink) 6%, transparent);
	}
	.shelf-box:first-child {
		margin-top: 0;
	}
	.shelf-head {
		display: flex;
		align-items: center;
		margin: 0;
		border-radius: var(--rad-control);
	}
	.shelf-head:has(.shelf:hover) {
		background: color-mix(in srgb, var(--ink) 4%, transparent);
	}
	.shelf {
		flex: 1;
		min-width: 0;
		display: flex;
		align-items: center;
		gap: 3px;
		box-sizing: border-box;
		padding: 3px 6px 3px 4px;
		font: inherit;
		font-size: 12px;
		font-weight: 500;
		line-height: 1.4;
		color: var(--ink);
		background: none;
		border: 0;
		border-radius: var(--rad-control);
		cursor: pointer;
		text-align: left;
	}
	.shelf-add {
		flex: none;
		border: 0;
		background: none;
		color: var(--ink-faint);
		font-size: 15px;
		line-height: 1;
		padding: 2px 7px;
		margin-right: 2px;
		border-radius: var(--rad-control);
		cursor: pointer;
	}
	.shelf-add:hover {
		color: var(--link);
		background: var(--link-wash);
	}
	.shelf .caret {
		width: 10px;
		color: var(--ink-faint);
	}
	.shelf .count {
		margin-left: auto;
		font-weight: 400;
		font-variant-numeric: tabular-nums;
		color: var(--ink-faint);
	}
	/* a top-level row starts where the head's caret does */
	.shelf-body {
		padding: 0 6px 6px 4px;
	}
	.closed summary {
		font-size: 10.5px;
		color: var(--ink-faint);
		margin: 0 0 var(--gap-hair) 6px;
		cursor: pointer;
	}
	/* the documents and the outline, each scrolling on its own, the line between them a few pixels of target round one hairline */
	.part {
		min-height: 0;
		overflow: auto;
	}
	.outline-part {
		flex: 1 1 0;
	}
	.outline-part :global(.contents) {
		margin: 0 0 var(--gap-tight) 6px;
	}
	ul.review-sections a {
		display: flex;
		flex-wrap: nowrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: 8px;
		font-size: 12px;
		padding: 3px 6px;
	}
	.review-sections a.here {
		color: var(--ink);
	}
	.review-sections a.here .section-name {
		font-weight: 600;
	}
	.section-name {
		flex: 1;
		min-width: 0;
	}
	.blurb {
		display: block;
		font-size: 11px;
		line-height: 1.35;
		font-weight: 400;
		color: var(--ink-faint);
	}
	.waits {
		flex: none;
		font-size: 10.5px;
		font-variant-numeric: tabular-nums;
		color: var(--ink-soft);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		padding: 0 6px;
	}
	.outline-divider {
		flex: none;
		height: 9px;
		margin: 0 -14px;
		cursor: row-resize;
		position: relative;
		touch-action: none;
	}
	.outline-divider::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: 4px;
		border-top: 1px solid var(--rule);
	}
	.outline-divider:hover::before,
	.outline-divider.moving::before,
	.outline-divider:focus-visible::before {
		border-top-color: var(--link);
	}
	.outline-divider:focus-visible {
		outline: none;
	}
	.outline-label .aside {
		text-transform: none;
		letter-spacing: 0;
	}
	/* The document being read carries the same weight as the current section in the contents, because they are the same
	   fact told twice: where you are. */
	.docs a.here {
		color: var(--ink);
		font-weight: 600;
	}
	.docs .aside {
		margin-left: 0.4em;
		color: var(--ink-faint);
		font-size: 0.9em;
	}
	/* Filled where a copy is filed, hollow where none is. */
	.library .aside {
		margin-left: 0.3em;
		color: var(--ink-faint);
		font-size: 0.9em;
	}
	/* A graph needs room beside its selection; on a narrow screen the selection follows it. */
	@media (max-width: 800px) {
		.shell-c:has(:global(main.graph)) > .panel { grid-row: 1 / span 2; }
		.shell-c:has(:global(main.graph)) > .content { grid-column: 2; grid-row: 1; }
		.shell-c:has(:global(main.graph)) > aside.right { grid-column: 2; grid-row: 2; width: auto; max-height: none; position: static; border-left: 0; border-top: 1px solid var(--rule); }
		.shell-c :global(main.graph) { height: 70vh; min-height: 400px; }
	}
</style>
