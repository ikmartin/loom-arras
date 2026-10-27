<script lang="ts">
	// The workspace (plan 0.13.3 W1, W6): one pane, or two of equal rank with one divider between them. Neither is primary — *what I am working on* is a fact about the reader's intent, not a property of a document, and a layout that encoded it would assert something only the reader knows.
	//
	// **One ratio, remembered.** A reader sets the shape of their screen once, so the ratio is a preference; it defaults to half, snaps at the middle and nowhere else, and a double-click puts it back there. The divider is one 3px rule, with a wider target than it draws, beneath the panes so what they open over the text stands over it. While a work is in either pane the divider stops short of squeezing its reading controls below about 420px (K5). **Below 700px one pane shows at a time**, under one strip holding both panes' tabs, the shown pane's toolbar beneath it: two panes on a phone are two unusable panes.
	//
	// **Compare is the workspace's.** The button is in the focused pane's toolbar, but what compare does to the panes stands here, mounted whichever pane is focused: both panes hide their annotations while it is pressed, so its washes and colours mean one thing each, and get back what they had when it is released; it ends when it can no longer be drawn; the publisher is asked once per pair; `[` and `]` step through the differences.
	import { untrack } from 'svelte';
	import { prefs } from '$lib/prefs.svelte';
	import Pane from './Pane.svelte';
	import PaneHead from './PaneHead.svelte';
	import { comparison, uncomparable } from './compare.svelte';
	import { workspace } from './store.svelte';
	import { settle, SNAP } from './divider';

	const STEP = 0.02;
	const NARROW = 700;
	const WORK_FLOOR = 420;

	let frame = $state<HTMLElement | null>(null);
	let width = $state(0);
	let dragging = $state(false);
	/** The ratio while a drag is in hand: drawn at most once a frame, and kept as the preference only on the drop, so the preferences are applied and stored once a drag rather than once a move. */
	let live = $state<number | null>(null);
	/** The frame's box, read once when a drag begins: it does not move while the divider does. */
	let box: DOMRect | null = null;
	let next: number | null = null;
	let painting = 0;

	const two = $derived(workspace.panes.length === 2);
	const narrow = $derived(width > 0 && width < NARROW);
	const works = $derived([0, 1].some((i) => workspace.active(i)?.kind === 'work'));
	const floor = $derived(works && width > 2 * WORK_FLOOR ? WORK_FLOOR / width : 0.2);
	const ratio = $derived(Math.min(1 - floor, Math.max(floor, live ?? prefs.divider)));
	$effect(() => {
		workspace.narrow = narrow;
	});

	const comparing = $derived(workspace.comparing);
	const why = $derived(uncomparable(workspace.narrow));
	// both panes hide their annotations while compare is pressed, and get back what they had once it is not
	$effect(() => {
		const pressed = comparing;
		untrack(() => (pressed ? workspace.suspendNotes() : workspace.resumeNotes()));
	});
	// a comparison that can no longer be drawn ends: the window narrowed, or a tab became something that does not pair
	$effect(() => {
		if (comparing && why) workspace.release();
	});
	// what one comparison found is forgotten when it ends, and the publisher is asked once per pair of items
	$effect(() => {
		const left = workspace.active(0);
		const right = workspace.active(1);
		if (!comparing || !left || !right) {
			comparison.reset();
			return;
		}
		void comparison.ask(left, right);
	});

	function steps(e: KeyboardEvent): void {
		if (!comparing || e.metaKey || e.ctrlKey || e.altKey) return;
		if ((e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable]')) return;
		if (e.key === ']') comparison.step(1);
		else if (e.key === '[') comparison.step(-1);
		else return;
		e.preventDefault();
	}

	/** Move the divider. */
	function set(next: number, snap = true): void {
		prefs.divider = settle(next, snap);
	}

	function drag(e: PointerEvent): void {
		if (!box) return;
		next = settle((e.clientX - box.left) / (box.width || 1));
		painting ||= requestAnimationFrame(() => {
			painting = 0;
			live = next;
		});
	}

	function grab(e: PointerEvent): void {
		if (!frame) return;
		dragging = true;
		workspace.resizing = true;
		box = frame.getBoundingClientRect();
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		drag(e);
	}

	function drop(e: PointerEvent): void {
		if (!dragging) return;
		dragging = false;
		(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
		cancelAnimationFrame(painting);
		painting = 0;
		if (next !== null) prefs.divider = next;
		live = next = box = null;
		workspace.resizing = false;
	}

	function key(e: KeyboardEvent): void {
		if (e.key === 'ArrowLeft') set(prefs.divider - STEP, false);
		else if (e.key === 'ArrowRight') set(prefs.divider + STEP, false);
		else if (e.key === 'Home') set(SNAP);
		else return;
		e.preventDefault();
	}
</script>

<svelte:window onresize={() => (width = frame?.clientWidth ?? width)} onkeydown={steps} />

<main class="workspace" class:dragging class:narrow bind:this={frame} bind:clientWidth={width} data-testid="workspace">
	{#if !workspace.panes.length}
		<p class="muted empty">Nothing is open. Choose a document in the panel.</p>
	{:else if narrow && two}
		<div class="strip" data-testid="narrow-strip">
			<div class="parts">
				{#each [0, 1] as i (i)}
					<div class="part" class:away={workspace.focus !== i}><PaneHead index={i} /></div>
				{/each}
			</div>
		</div>
		{#key workspace.focus}<Pane index={workspace.focus} head={false} style="flex: 1 1 auto" />{/key}
	{:else}
		<!-- one element for the first pane however many there are: a second pane opening beside must not re-create the first, and lose what the reader was doing in it -->
		<!-- the first pane's own width, never a custom property on the workspace: both documents would inherit it, and every move of the divider would restyle every element of both -->
		<Pane index={0} style={two ? `flex: 0 0 ${ratio * 100}%` : 'flex: 1 1 auto'} />
		{#if two}
			<!-- A separator that takes focus is a widget in ARIA's own terms — a window splitter, with the arrow keys and aria-valuenow this one has — so the two rules below are being told about a case they do not model. -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
			<div
				class="divider"
				role="separator"
				tabindex="0"
				aria-label="Resize the panes"
				aria-orientation="vertical"
				aria-valuenow={Math.round(ratio * 100)}
				aria-valuemin={20}
				aria-valuemax={80}
				data-testid="divider"
				onpointerdown={grab}
				onpointermove={(e) => dragging && drag(e)}
				onpointerup={drop}
				onpointercancel={drop}
				ondblclick={() => set(SNAP)}
				onkeydown={key}
			></div>
			<Pane index={1} style="flex: 1 1 0" />
		{/if}
	{/if}
</main>

<style>
	.workspace {
		display: flex;
		align-items: stretch;
		min-width: 0;
		height: 100vh;
		overflow: hidden;
	}
	.workspace.narrow {
		flex-direction: column;
	}
	.empty {
		padding: var(--gap-wide);
	}
	/* One line, drawn in the middle of a wider target: a 3px rule is where the eye wants the boundary, and no hand can hit it. The target is a column of its own rather than overlapping the panes, and it stands beneath them, so a box a pane opens over the text is drawn over the divider and not under it. */
	.divider {
		flex: 0 0 auto;
		width: 9px;
		position: relative;
		z-index: 0;
		cursor: col-resize;
		background: none;
		touch-action: none;
	}
	.divider::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		left: 3px;
		width: 3px;
		background: var(--rule-strong);
	}
	.divider:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: -2px;
	}
	/* the comparison's gutter is drawn against the text's lines, which move while the divider does; it is drawn again at the drop */
	.workspace.dragging :global(.compare-gutter) {
		visibility: hidden;
	}
	.workspace.dragging .divider::before,
	.divider:hover::before {
		background: var(--ink-faint);
	}
	/* Below the two-pane width: one strip, the shown item's views first and then both panes' tabs, the unfocused pane's quieter, and one body under it. */
	.strip {
		display: flex;
		flex: 0 0 var(--tab-h);
		min-width: 0;
		background: var(--leaf);
		border-bottom: 1px solid var(--rule);
	}
	.parts {
		display: flex;
		flex: 0 1 auto;
		min-width: 0;
		overflow-x: auto;
		scrollbar-width: none;
	}
	.strip .part {
		display: flex;
		flex: 0 0 auto;
	}
	.strip .part + .part {
		border-left: 1px solid var(--rule-strong);
	}
	.strip .part.away {
		opacity: 0.7;
	}
	.strip .part :global(.head) {
		flex: 0 0 auto;
		border-bottom: 0;
	}
</style>
