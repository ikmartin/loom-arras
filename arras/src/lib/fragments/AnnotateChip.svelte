<script lang="ts">
	// The one annotate chip (book 15.3.1): a selection stays a selection, and this offers the other thing. It stands at the selection's end in the annotation neutral, on the text and on a PDF page alike, follows that end as the page scrolls, and Enter does what a press on it does. The caller shows it while a selection is offered and takes it down once the composer opens.
	type Box = { left: number; top: number; width: number; height: number };

	let {
		at,
		range,
		onaccept
	}: {
		/** The selection's bounding box, in window coordinates when it was made: where the chip stands when there is no range, and so it does not follow a scroll. */
		at: Box;
		/** The selection itself, when the caller has it: the chip stands after its last line, re-measured on every scroll, and is hidden while that line is scrolled out of view or no longer in the page. */
		range?: Range;
		onaccept: () => void;
	} = $props();

	/** Room kept from the selection's last line, and from the window's edges. */
	const GAP = 6;
	let el = $state<HTMLButtonElement | null>(null);

	/** Bumped by a scroll anywhere in the page, and by a resize of the window or of a scroller below: the chip is fixed and the words are not, so each one means measuring the range again. */
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

	/** Every ancestor of the selection's end that scrolls: a pane's body, the page. Found once; their boxes are read on each move. A box that only hides its overflow is not one, since KaTeX sizes those tighter than the line boxes inside them. */
	const clips = $derived.by<Element[]>(() => {
		const out: Element[] = [];
		const from = range?.endContainer;
		for (let n = from instanceof Element ? from : (from?.parentElement ?? null); n && n !== document.body; n = n.parentElement) {
			const s = getComputedStyle(n);
			if (/auto|scroll/.test(`${s.overflowX} ${s.overflowY}`)) out.push(n);
		}
		return out;
	});
	// a pane narrowed or widened reflows the words with no scroll and no window resize
	$effect(() => {
		const watch = new ResizeObserver(() => moved++);
		for (const c of clips) watch.observe(c);
		return () => watch.disconnect();
	});

	/** Where the selection ends now: the last of its line boxes, or the box the caller measured when there is no range. Null when the range has no box left, as on a PDF page dropped from the window. */
	const end = $derived.by<Box | null>(() => {
		void moved;
		if (!range) return at;
		const last = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0).at(-1);
		return last ? { left: last.left, top: last.top, width: last.width, height: last.height } : null;
	});

	/** Whether the end of the selection's last line can be seen: inside the window and inside every box that clips it, so the chip never stands over a pane's toolbar or the other pane once its words have scrolled away. */
	const seen = $derived.by(() => {
		if (!end) return false;
		const x = end.left + end.width - 1;
		const y = end.top + end.height / 2;
		const inside = (r: { left: number; top: number; right: number; bottom: number }) => x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
		return inside({ left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight }) && clips.every((c) => inside(c.getBoundingClientRect()));
	});

	/** After the end of the selection's last line, level with it; below it when the window's right edge is too near. Measured once the chip is in the page, since its width depends on its face. */
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

	// Enter while a selection is offered is the chip pressed. Not while typing, and not with a modifier: those are somebody else's keys.
	$effect(() => {
		const key = (e: KeyboardEvent) => {
			if (e.key !== 'Enter' || e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
			if ((e.target as HTMLElement | null)?.closest('input, textarea, select, [contenteditable]')) return;
			e.preventDefault();
			onaccept();
		};
		document.addEventListener('keydown', key);
		return () => document.removeEventListener('keydown', key);
	});
</script>

<button type="button" class="chip" bind:this={el} data-testid="annotate-offer" style="left: {place.left}px; top: {place.top}px;" style:visibility={seen ? null : 'hidden'} onmousedown={(e) => e.preventDefault()} onclick={onaccept}>annotate</button>

<style>
	/* Fixed, because the rect it is placed by is the selection's own client rect, re-read on every scroll. Pressing it must not end the selection, which is why the mousedown is swallowed. */
	.chip {
		position: fixed;
		z-index: 30;
		font-family: var(--sans);
		/* the reader's chosen body size (Settings), so the offer reads at the size of the words it is offered on */
		font-size: var(--body-size);
		line-height: 1;
		padding: 0.35em 0.8em;
		border-radius: var(--rad-pill);
		border: 1px solid var(--rule);
		background: var(--sheet);
		color: var(--ann-neutral);
		box-shadow: 0 2px 8px rgb(0 0 0 / 14%);
		cursor: pointer;
	}
	/* The hover tint is laid over the sheet, never left translucent: the chip stands over the words, which a see-through face lets show through its label. */
	.chip:hover {
		background: color-mix(in srgb, var(--ann-neutral) 10%, var(--sheet));
		border-color: var(--ann-neutral);
	}
</style>
