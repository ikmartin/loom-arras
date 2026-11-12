<script lang="ts">
	// What stands at the end of a selection: Quote on a bare selection, Add comment after Annotate marked one. After the end of the selection's last line, level with it, below it near the window's right edge; it follows that end as the page scrolls and hides while it is scrolled out of view. Pressing it must not end the selection, which is why the mousedown is swallowed.
	import type { Snippet } from 'svelte';

	type Box = { left: number; top: number; width: number; height: number };

	let {
		at,
		range,
		children
	}: {
		/** The selection's bounding box, in window coordinates when it was made: where the chip stands when there is no range, and so it does not follow a scroll. */
		at: Box;
		/** The selection itself, when the caller has it: re-measured on every scroll. */
		range?: Range;
		children: Snippet;
	} = $props();

	/** Room kept from the selection's last line, and from the window's edges. */
	const GAP = 6;
	let el = $state<HTMLElement | null>(null);

	/** Bumped by a scroll anywhere in the page, and by a resize of the window or of a scroller below: the chip is fixed and the words are not. */
	let moved = $state(0);
	$effect(() => {
		const bump = () => moved++;
		window.addEventListener('scroll', bump, { capture: true, passive: true });
		window.addEventListener('resize', bump);
		return () => {
			window.removeEventListener('scroll', bump, { capture: true });
			window.removeEventListener('resize', bump);
		};
	});

	/** Every ancestor of the selection's end that scrolls, found once; their boxes are read on each move. */
	const clips = $derived.by<Element[]>(() => {
		const out: Element[] = [];
		const from = range?.endContainer;
		for (let n = from instanceof Element ? from : (from?.parentElement ?? null); n && n !== document.body; n = n.parentElement) {
			const s = getComputedStyle(n);
			if (/auto|scroll/.test(`${s.overflowX} ${s.overflowY}`)) out.push(n);
		}
		return out;
	});
	$effect(() => {
		const watch = new ResizeObserver(() => moved++);
		for (const c of clips) watch.observe(c);
		return () => watch.disconnect();
	});

	/** Where the selection ends now: the last of its line boxes, or the box the caller measured. Null when the range has no box left. */
	const end = $derived.by<Box | null>(() => {
		void moved;
		if (!range) return at;
		const last = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0).at(-1);
		return last ? { left: last.left, top: last.top, width: last.width, height: last.height } : null;
	});

	/** Whether the end of the selection's last line can be seen: inside the window and inside every box that clips it. */
	const seen = $derived.by(() => {
		if (!end) return false;
		const x = end.left + end.width - 1;
		const y = end.top + end.height / 2;
		const inside = (r: { left: number; top: number; right: number; bottom: number }) => x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
		return inside({ left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight }) && clips.every((c) => inside(c.getBoundingClientRect()));
	});

	const place = $derived.by(() => {
		const w = el?.offsetWidth ?? 64;
		const h = el?.offsetHeight ?? 22;
		if (!end) return { left: 0, top: 0 };
		let left = end.left + end.width + GAP;
		let top = end.top + end.height / 2 - h / 2;
		if (left + w > window.innerWidth - GAP) {
			left = Math.max(GAP, end.left + end.width - w);
			top = end.top + end.height + GAP;
		}
		return { left: Math.round(left), top: Math.round(Math.min(Math.max(GAP, top), window.innerHeight - h - GAP)) };
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<span class="at-selection" bind:this={el} style="left: {place.left}px; top: {place.top}px;" style:visibility={seen ? null : 'hidden'} onmousedown={(e) => e.preventDefault()}>
	{@render children()}
</span>

<style>
	.at-selection {
		position: fixed;
		z-index: 35;
		display: flex;
		gap: 4px;
	}
	.at-selection :global(.chip) {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 28px;
		padding: 0 10px;
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule-strong);
		border-radius: 14px;
		box-shadow: var(--float-shadow);
		cursor: pointer;
	}
	.at-selection :global(.chip:hover) {
		background: var(--leaf);
	}
</style>
