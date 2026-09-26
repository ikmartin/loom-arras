<script lang="ts">
	// The focused pane's toolbar (plan 0.16 decisions 7–9; book 15.2.5): one line at the pane's top right, on the pane's own layer so the text never moves for it — the kind's bar, then **view ▾**, the Popover holding every other control in full words, then the pin. Each kind's controls draw one, so the pane that is not focused draws none.
	//
	// **It floats.** It shows while the pointer is in a band across the top of the pane's body — 96px tall, inset 96px from the left and 4px from the right, clamped so it always holds the bar — and fades over 0.4s when the pointer leaves; it is held while the pointer is on it, while its menu is open, while keyboard focus is in it, and while pinned. Keyboard focus anywhere in the pane shows it for a while. Nothing draws the band.
	import { tick, type Snippet } from 'svelte';
	import Popover from '$lib/components/Popover.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { getPane } from './state.svelte';

	let {
		name,
		bar,
		view,
		on = false
	}: {
		/** The item's name, for every control's accessible name. */
		name: string;
		/** What stands on the bar before *view*; omitted when nothing does, and then no divider is drawn. */
		bar?: Snippet;
		/** The lines of the *view* menu (ToolbarItem), an `hr` between groups. */
		view: Snippet;
		/** A mode inside *view* is on: the dot on *view* says so. */
		on?: boolean;
	} = $props();

	const BAND = { height: 96, left: 96, right: 4 };
	const TIP = {
		pinned: 'Fade: let these controls fade when the pointer leaves the top of the pane.',
		fade: "Don't fade: keep these controls showing until you click again."
	};

	const pane = getPane();
	const uid = $props.id();
	let root = $state<HTMLElement | null>(null);
	let viewButton = $state<HTMLButtonElement | null>(null);
	let list = $state<HTMLElement | null>(null);
	let menu = $state(false);
	let shown = $state(true);
	const pinned = $derived(prefs.controls === 'pinned');

	let timer: ReturnType<typeof setTimeout> | undefined;
	let over = false;
	let inside = false;

	const held = () => pinned || menu || over || !!root?.querySelector(':focus-visible');
	function show(): void {
		clearTimeout(timer);
		shown = true;
	}
	function hide(): void {
		if (!held()) shown = false;
	}
	function arm(ms: number): void {
		clearTimeout(timer);
		timer = setTimeout(hide, ms);
	}

	/** Whether the pointer is in the band: measured from the pane's body each time, so a resized pane or a wider bar needs no bookkeeping. */
	function within(e: PointerEvent): boolean {
		const body = pane.scroller();
		if (!body || !root) return false;
		const o = body.getBoundingClientRect();
		const b = root.getBoundingClientRect();
		const right = Math.min(BAND.right, Math.max(0, o.right - b.right - 4));
		const left = Math.min(BAND.left, Math.max(0, b.left - o.left - 4));
		const height = Math.max(BAND.height, b.bottom - o.top + 8);
		return e.clientY >= o.top && e.clientY <= o.top + Math.min(height, o.height) && e.clientX >= o.left + left && e.clientX <= o.right - right;
	}

	$effect(() => {
		const el = pane.frame();
		if (!el) return;
		const move = (e: PointerEvent) => {
			const now = within(e);
			if (now) show();
			else if (inside) arm(0);
			inside = now;
		};
		const leave = () => {
			inside = false;
			arm(0);
		};
		// keyboard focus only: a press on the text also focuses, and must not wake the bar
		const focus = (e: FocusEvent) => {
			if (!(e.target instanceof Element) || !e.target.matches(':focus-visible')) return;
			show();
			if (!root?.contains(e.target)) arm(2500);
		};
		el.addEventListener('pointermove', move);
		el.addEventListener('pointerleave', leave);
		el.addEventListener('focusin', focus);
		return () => {
			el.removeEventListener('pointermove', move);
			el.removeEventListener('pointerleave', leave);
			el.removeEventListener('focusin', focus);
			clearTimeout(timer);
		};
	});

	// pinned or with its menu open it stays; otherwise it is shown a moment, so a reader sees where it went, and then fades unless the pointer holds it
	$effect(() => {
		if (pinned || menu) show();
		else arm(600);
	});

	function flip(): void {
		prefs.controls = pinned ? 'fade' : 'pinned';
	}

	function items(): HTMLElement[] {
		return [...(list?.querySelectorAll<HTMLElement>('[role^="menuitem"]') ?? [])];
	}

	/** Close the menu, handing focus back to *view* when it was inside, so a keyboard reader is not left on nothing. */
	function close(): void {
		const had = !!list?.contains(document.activeElement);
		menu = false;
		if (had) viewButton?.focus();
	}

	async function toggle(): Promise<void> {
		menu = !menu;
		if (!menu) return;
		await tick();
		items()[0]?.focus();
	}

	function keys(e: KeyboardEvent): void {
		const all = items();
		const at = all.indexOf(document.activeElement as HTMLElement);
		const to = e.key === 'ArrowDown' ? at + 1 : e.key === 'ArrowUp' ? at - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? all.length - 1 : null;
		if (to === null || !all.length) return;
		e.preventDefault();
		all[(to + all.length) % all.length].focus();
	}

	// a line chosen closes the menu, after its own handler has run; a greyed one does nothing
	function chosen(e: MouseEvent): void {
		const it = (e.target as Element).closest('[role^="menuitem"]');
		if (it && it.getAttribute('aria-disabled') !== 'true') close();
	}
</script>

<div
	class="toolbar"
	class:gone={!shown}
	role="group"
	aria-label="controls for {name}"
	data-testid="item-controls"
	data-shown={shown}
	bind:this={root}
	onpointerenter={() => (over = true)}
	onpointerleave={() => {
		over = false;
		if (!inside) arm(0);
	}}
	onfocusout={() => arm(2500)}
>
	{#if bar}<span class="bar">{@render bar()}</span>{/if}
	<Popover bind:open={menu} placement="below" align="end" width={230} onclose={close}>
		{#snippet trigger()}
			<span class="end">
				<button
					type="button"
					class="view"
					class:divided={!!bar}
					aria-haspopup="menu"
					aria-expanded={menu}
					aria-label="view menu for {name}"
					data-testid="toolbar-view"
					bind:this={viewButton}
					onclick={toggle}
					>view{#if on}<span class="dot" aria-hidden="true" data-testid="toolbar-view-on"></span>{/if}<svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"
						><path d="M4.5 6.5 L8 10 L11.5 6.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></svg
					></button
				><button type="button" class="pin" aria-pressed={pinned} aria-label={pinned ? 'fade' : "don't fade"} aria-describedby="{uid}-tip" data-testid="toolbar-pin" onclick={flip}
					><svg viewBox="0 0 16 16" aria-hidden="true"
						><path class="head" d="M6 2.5 H10 L9.3 6.5 L11.5 8.8 H4.5 L6.7 6.5 Z" stroke="currentColor" stroke-linejoin="round" /><path class="needle" d="M8 8.8 V13.5" stroke="currentColor" stroke-linecap="round" /></svg
					><span class="tip" role="tooltip" id="{uid}-tip" data-testid="toolbar-pin-tip">{pinned ? TIP.pinned : TIP.fade}</span></button
				>
			</span>
		{/snippet}
		<!-- svelte-ignore a11y_click_events_have_key_events (a menu item is a button or a link, whose Enter and Space arrive as clicks) -->
		<div class="menu" role="menu" tabindex="-1" aria-label="view of {name}" data-testid="toolbar-menu" bind:this={list} onkeydown={keys} onclick={chosen}>
			{@render view()}
		</div>
	</Popover>
</div>

<style>
	/* over the page on the pane's own layer, never in the body that scrolls; below the head, or at the top of a pane that has none */
	.toolbar {
		position: absolute;
		top: var(--toolbar-top, 8px);
		right: 16px;
		z-index: 30;
		display: flex;
		align-items: center;
		gap: 2px;
		padding: 2px;
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink-soft);
		white-space: nowrap;
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		box-shadow: var(--float-shadow);
		transition: opacity 0.4s ease;
	}
	.toolbar.gone {
		opacity: 0;
		pointer-events: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.toolbar {
			transition: none;
		}
	}
	.bar,
	.end {
		display: flex;
		align-items: center;
		gap: 2px;
	}
	.view {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		margin-left: 2px;
		padding: 2px 8px 2px 9px;
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 0;
		cursor: pointer;
	}
	/* the divider before view, only when something stands to its left */
	.view.divided {
		border-left: 1px solid var(--rule);
	}
	.view:hover,
	.view[aria-expanded='true'] {
		color: var(--ink);
	}
	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--link);
	}
	.pin {
		position: relative;
		display: inline-grid;
		place-items: center;
		width: 24px;
		height: 22px;
		margin-left: 2px;
		padding: 0 0 0 2px;
		color: var(--ink-faint);
		background: none;
		border: 0;
		border-left: 1px solid var(--rule);
		cursor: pointer;
	}
	/* off: a loose pin, tilted, a thin outline in the faint ink; on: upright, filled and heavier, in the link's colour on its wash */
	.pin svg {
		width: 14px;
		height: 14px;
		fill: none;
		stroke-width: 1.2px;
		transform: rotate(35deg);
		transition: transform 0.15s;
	}
	.pin:hover {
		color: var(--ink-soft);
	}
	.pin[aria-pressed='true'] {
		color: var(--link);
		background: var(--link-wash);
		border-radius: 0 6px 6px 0;
	}
	.pin[aria-pressed='true'] svg {
		transform: none;
		stroke-width: 1.8px;
	}
	.pin[aria-pressed='true'] .head {
		fill: currentColor;
	}
	.view:focus-visible,
	.pin:focus-visible {
		outline: 2px solid var(--link);
		outline-offset: 2px;
		border-radius: 4px;
	}
	.tip {
		position: absolute;
		top: calc(100% + 8px);
		right: -4px;
		width: 220px;
		padding: 6px 9px;
		font-size: 11.5px;
		line-height: 1.4;
		text-align: left;
		white-space: normal;
		color: var(--paper);
		background: var(--ink);
		border-radius: 6px;
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.12s;
		z-index: 5;
	}
	.pin:hover .tip,
	.pin:focus-visible .tip {
		opacity: 1;
	}
	.menu {
		padding: 6px 0;
		font-family: var(--sans);
		font-size: 12.5px;
		outline: none;
	}
	.menu :global(hr) {
		border: 0;
		border-top: 1px solid var(--rule);
		margin: 5px 0;
	}
</style>
