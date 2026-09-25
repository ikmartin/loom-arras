<script lang="ts">
	// The one annotate chip (book 15.3.1): a selection stays a selection, and this offers the other thing. It stands at the selection's end in the annotation neutral, on the text and on a PDF page alike, and Enter does what a press on it does. The caller shows it while a selection is offered and takes it down once the composer opens.
	type Box = { left: number; top: number; width: number; height: number };

	let {
		at,
		range,
		onaccept
	}: {
		/** The selection's bounding box, in window coordinates: where the chip stands when the range gives no better answer. */
		at: Box;
		/** The selection itself, when the caller has it: the chip stands after its last line rather than at the corner of its bounding box. */
		range?: Range;
		onaccept: () => void;
	} = $props();

	/** Room kept from the selection's last line, and from the window's edges. */
	const GAP = 6;
	let el = $state<HTMLButtonElement | null>(null);

	/** Where the selection ends: the last of its line boxes, else its bounding box. */
	const end = $derived.by<Box>(() => {
		const rects = range ? [...range.getClientRects()] : [];
		const last = rects.filter((r) => r.width > 0 && r.height > 0).at(-1);
		return last ? { left: last.left, top: last.top, width: last.width, height: last.height } : at;
	});

	/** After the end of the selection's last line, level with it; below it when the window's right edge is too near. Measured once the chip is in the page, since its width depends on its face. */
	const place = $derived.by(() => {
		const w = el?.offsetWidth ?? 64;
		const h = el?.offsetHeight ?? 22;
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

<button type="button" class="chip" bind:this={el} data-testid="annotate-offer" style="left: {place.left}px; top: {place.top}px;" onmousedown={(e) => e.preventDefault()} onclick={onaccept}>annotate</button>

<style>
	/* Fixed, because the rect it is placed by is the selection's own client rect. Pressing it must not end the selection, which is why the mousedown is swallowed. */
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
