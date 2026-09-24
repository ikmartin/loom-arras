<script lang="ts">
	// Hover previews (plan 0.13.3 H1–H7, book 15.3.6): resting on a link shows what is behind it, so a reader can check what a result rests on, or what uses it, without following it. **A card renders an item**: the link is read as the item it names and the registry's small render draws it, so this component owns only the card — its timing, its place against the window, its dismissal and `open here` — and knows no kind of its own. A kind with no small render previews nothing.
	// The timing is the author's site generator's: 300ms before showing, so crossing a paragraph of links does not flicker; 200ms of grace to move into the card, which stays while the pointer is inside it; Escape, a press elsewhere or a scroll outside the card dismisses it. There is no preview on a device that cannot hover.
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { keyUrl } from '$lib/nav';
	import { pageOf } from '$lib/worklink';
	import { itemForHref, paneOfElement } from '$lib/workspace/links';
	import { itemFromPath, itemKey, type Item } from '$lib/workspace/item';
	import { kinds } from '$lib/workspace/registry';
	import { workspace } from '$lib/workspace/store.svelte';

	const SHOW_MS = 300;
	const HIDE_MS = 200;

	// raw, so the identity check after an await compares the object that was hovered rather than a proxy of it
	let target = $state.raw<Item | null>(null);
	let card: HTMLElement | undefined = $state();
	let left = $state(0);
	let top = $state(0);
	let anchor: Element | null = null;
	/** What the hovered link names and the pane it stands in, for the card's one action: opening it in that pane, the destination a click does not give (H6). */
	let opens = $state.raw<{ item: Item; pane: number } | null>(null);
	let showTimer: ReturnType<typeof setTimeout> | undefined;
	let hideTimer: ReturnType<typeof setTimeout> | undefined;

	const m = $derived(store.manifest);
	const kind = $derived(target ? kinds[target.kind] : null);

	/**
	 * The item a hovered link names, if it is one a card can show.
	 *
	 * Read through the item codec, which strips the app's base path, so a link built with `route()` resolves under any base. Two decisions are the hover's own and stay here: a digest result with a filed paper and a located page previews the paper at that result rather than the transcription; and a citation to a work that names no page by URL may name one in its postnote, and one that names a place nobody can find previews nothing (H5).
	 */
	function hoverItem(a: Element): Item | null {
		if (!m || a.closest('.link-preview, [data-no-preview]')) return null;
		const owner = (key: string) => {
			const region = m.regions[key];
			const k = region ? region.container : key;
			const n = m.keys[k]?.node ?? k;
			return m.nodes[n] ? n : null;
		};
		/** **A digest node previews the paper, not the digest**: a result read off a cited work is a transcription of a page, and a reader hovering a citation wants the page. With no copy filed, or no page in the locator, the transcription is the best there is. */
		const nodeOrPaper = (n: string): Item => {
			const nd = m.nodes[n];
			const work = nd?.digest ? m.references[nd.digest] : undefined;
			const at = pageOf(nd?.locator);
			return work?.artifacts?.pdf && at ? { kind: 'work', id: work.citekey, place: { page: at, result: n } } : { kind: 'node', id: n };
		};
		const named = a.getAttribute('data-preview-key') ?? (a.matches('a.ref[data-target]') ? a.getAttribute('data-target') : a.closest<HTMLElement>('span.cite[data-target]')?.dataset.target);
		let item: Item | null = null;
		if (named) {
			const n = owner(named);
			item = n ? nodeOrPaper(n) : null;
		} else {
			const href = a.getAttribute('href');
			if (!href) return null;
			item = itemForHref(m, href);
			if (item?.kind === 'node') {
				const n = owner(item.id);
				item = n ? nodeOrPaper(n) : null;
			} else if (item?.kind === 'work') {
				// the page itself when a copy is filed; otherwise nothing to show
				if (!m.references[item.id]?.artifacts?.pdf) return null;
				// A citation carrying a postnote names a place, not a work. Where the postnote is a digest node, `named` above already previewed it; here the postnote is all there is to go on, and one that names no page is a place unknown, whose honest preview is none. A bare citation names the work, so its front page stands.
				const postnote = a.closest<HTMLElement>('span.cite')?.dataset.postnote;
				if (!item.place?.page && postnote) {
					const at = pageOf(postnote);
					if (!at) return null;
					item = { ...item, place: { ...item.place, page: at } };
				}
			}
		}
		if (!item || !kinds[item.kind].preview) return null;
		// what the link's own pane is already showing, or the current item for a link in no pane, previews nothing a reader cannot already see
		const pane = paneOfElement(a);
		const showing = pane >= 0 ? workspace.active(pane) : workspace.current;
		if (showing && itemKey(showing) === itemKey(item)) return null;
		return item;
	}

	function hide() {
		clearTimeout(showTimer);
		clearTimeout(hideTimer);
		target = null;
		anchor = null;
		opens = null;
	}

	function hideSoon() {
		clearTimeout(showTimer);
		clearTimeout(hideTimer);
		hideTimer = setTimeout(hide, HIDE_MS);
	}

	async function place() {
		await tick();
		if (!card || !anchor) return;
		const w = card.offsetWidth;
		const h = card.offsetHeight;
		const pad = 8;
		// a drawing at the window's edge asks for its cards beside it, so a card never covers the drawing's own controls
		const side = anchor.closest<HTMLElement>('[data-preview-side="left"]');
		if (side) {
			const s = side.getBoundingClientRect();
			const a = anchor.getBoundingClientRect();
			left = Math.max(pad, s.left - w - pad);
			top = Math.min(Math.max(pad, a.top - h / 2), window.innerHeight - h - pad);
			return;
		}
		const r = anchor.getBoundingClientRect();
		let x = r.left;
		let y = r.bottom + pad;
		if (x + w > window.innerWidth - pad) x = window.innerWidth - w - pad;
		if (x < pad) x = pad;
		// above the link when there is no room below
		if (y + h > window.innerHeight - pad && r.top - h - pad > pad) y = r.top - h - pad;
		left = x;
		top = y;
	}

	function show(a: Element, t: Item) {
		if (!m) return;
		anchor = a;
		target = t;
		const pane = paneOfElement(a);
		// `open here` opens what a click would, at the same place: the link's own item where it has an href, else the one the card shows
		const href = a.getAttribute('href');
		const clicked = href ? itemForHref(m, href) : null;
		const item = clicked ?? (t.kind === 'node' ? itemFromPath(m, keyUrl(m, t.id)) : t);
		opens = item && pane >= 0 ? { item, pane } : null;
		void place();
	}

	onMount(() => {
		if (!window.matchMedia('(hover: hover)').matches) return;
		// `pending` is the link waiting out the delay; `anchor` is the link whose card is showing
		let pending: Element | null = null;
		const over = (e: MouseEvent) => {
			const el = e.target as Element | null;
			if (el?.closest?.('.link-preview')) {
				clearTimeout(hideTimer);
				return;
			}
			const a = el?.closest?.('a') ?? null;
			if (!a || a === pending) return;
			if (a === anchor) {
				clearTimeout(hideTimer);
				return;
			}
			const t = hoverItem(a);
			if (!t) return;
			pending = a;
			if (m) kinds[t.kind].prefetch?.(t, m);
			clearTimeout(showTimer);
			showTimer = setTimeout(() => {
				pending = null;
				void show(a, t);
			}, SHOW_MS);
		};
		const out = (e: MouseEvent) => {
			const from = e.target as Element | null;
			const to = e.relatedTarget as Node | null;
			const fromLink = from?.closest?.('a');
			if (pending && fromLink === pending && !(to && pending.contains(to))) {
				clearTimeout(showTimer);
				pending = null;
			}
			if (anchor && (fromLink === anchor || from?.closest?.('.link-preview'))) {
				const toEl = to instanceof Element ? to : (to?.parentElement ?? null);
				if (toEl && (anchor.contains(toEl) || toEl.closest('.link-preview'))) return;
				hideSoon();
			}
		};
		const key = (e: KeyboardEvent) => e.key === 'Escape' && hide();
		// **A scroll inside the card is not the page moving out from under it.** The listener is capturing, so it hears
		// every scroll in the document — including the one a PDF preview makes when it scrolls its own column to the
		// page it was asked for, which closed the card in the same frame it opened.
		const scroll = (e: Event) => {
			if (!target) return;
			const from = e.target as Element | null;
			if (from?.closest?.('.link-preview')) return;
			hide();
		};
		const down = (e: PointerEvent) => {
			if (target && !(e.target as Element)?.closest?.('.link-preview')) hide();
		};
		document.addEventListener('mouseover', over);
		document.addEventListener('mouseout', out);
		document.addEventListener('keydown', key);
		document.addEventListener('pointerdown', down, true);
		window.addEventListener('scroll', scroll, { capture: true, passive: true });
		return () => {
			hide();
			document.removeEventListener('mouseover', over);
			document.removeEventListener('mouseout', out);
			document.removeEventListener('keydown', key);
			document.removeEventListener('pointerdown', down, true);
			window.removeEventListener('scroll', scroll, { capture: true });
		};
	});

	// a navigation replaces the page the card was about
	$effect(() => {
		void page.url.pathname;
		hide();
	});
</script>

{#if target && m && kind?.preview}
	{@const Preview = kind.preview}
	<div class="link-preview" class:bleeds={kind.bleeds} role="tooltip" bind:this={card} style="left: {left}px; top: {top}px" data-testid="link-preview">
		{#key itemKey(target) + (target.place?.page ?? '') + (target.place?.result ?? '')}<Preview item={target} onresize={() => void place()} />{/key}
		{#if opens}
			<!-- Drawn always, not revealed once the pointer is inside: a remedy most readers never find is no remedy (H6). A click opens the target in the other pane; this opens it in the link's own, or reveals it where it is already open. -->
			<p class="opens">
				<button
					type="button"
					class="as-link"
					data-testid="preview-open-here"
					onclick={() => {
						if (opens) workspace.openIn(opens.item, opens.pane);
						hide();
					}}>open here</button
				>
			</p>
		{/if}
	</div>
{/if}

<style>
	.opens {
		display: flex;
		align-items: baseline;
		gap: var(--gap);
		margin: var(--gap-tight) 0 0;
		padding: var(--gap-hair) 0 0;
		border-top: 1px solid var(--rule);
	}
	/* a card with no padding of its own gives its line some */
	.link-preview.bleeds .opens {
		margin: 0;
		padding: var(--gap-hair) var(--gap);
		background: var(--leaf);
	}
	.link-preview {
		position: fixed;
		z-index: 60;
		width: max-content;
		max-width: min(26rem, calc(100vw - 16px));
		min-width: 14rem;
		padding: var(--gap-tight) var(--gap);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-card);
		box-shadow: 0 6px 24px rgb(0 0 0 / 13%);
		font-family: var(--sans);
		font-size: 11px;
		line-height: 1.5;
	}
	/* a card whose small render is its own frame — a page — has no padding and no border inside the card's own; the radius is inherited and clipped so the page takes the corners */
	.link-preview.bleeds {
		padding: 0;
		overflow: hidden;
		max-width: min(46.8rem, calc(100vw - 16px));
	}
	@media (hover: none) {
		.link-preview {
			display: none;
		}
	}
</style>
