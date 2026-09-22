<script lang="ts">
	// Hover previews (book 15.3.6): resting on a link to a node or a reference shows what is behind it, so a reader can check what a result depends on, or what uses it, without leaving the page.
	// The behaviour is the author's site generator's, carried over: a 300ms delay so crossing a paragraph of links does not flicker, a 200ms grace to travel into the card, a card that stays while the pointer is inside it so its own links work, and Escape or any scroll to dismiss. There is no preview on a device that cannot hover.
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { fetchFragment } from '$lib/fragments/fetch';
	import { wire } from '$lib/fragments/mount';
	import { typeset } from '$lib/math/mathjax';
	import { keyFromParam } from '$lib/nav';
	import { nodeBadge } from '$lib/badges';
	import { bibText } from '$lib/works';
	import { isWorkLink, locate, pageOf, parseWorkLink, readKeys, type WorkLink } from '$lib/worklink';
	import { artifactUrl, dataUrl } from '$lib/paths';
	import type { Sidecar } from '$lib/pdf/sidecar';
	import { can, write, type WriteResult } from '$lib/write';
	import Badge from './Badge.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from './WorkLinks.svelte';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';

	const SHOW_MS = 300;
	const HIDE_MS = 200;

	// A `cited:` link with a copy here previews the page itself, at the place (plan 0.13 item 5: the renderer's fourth
	// mounting context); one without previews the work's record.
	type Target =
		| { kind: 'node'; key: string }
		| { kind: 'ref'; citekey: string }
		| { kind: 'work'; citekey: string; link: WorkLink; url: string; result?: string };

	// raw, so the identity check after an await compares the object that was hovered rather than a proxy of it
	let target = $state.raw<Target | null>(null);
	let html = $state('');
	let card: HTMLElement | undefined = $state();
	let body: HTMLElement | undefined = $state();
	let left = $state(0);
	let top = $state(0);
	let anchor: Element | null = null;
	let showTimer: ReturnType<typeof setTimeout> | undefined;
	let hideTimer: ReturnType<typeof setTimeout> | undefined;

	const m = $derived(store.manifest);
	const node = $derived(m && target?.kind === 'node' ? m.nodes[target.key] : undefined);
	const ref = $derived(m && (target?.kind === 'ref' || target?.kind === 'work') ? m.references[target.citekey] : undefined);
	/** The place the link names, mapped by the publisher into rectangles for the card to draw; a box needs no mapping. */
	let lit = $state<{ page: number; rects: number[][] } | null>(null);
	/**
	 * The statement's own lines, from the work's sidecar.
	 *
	 * **A citation previews the result, not the sheet it is printed on.** The card is sized to the statement plus two
	 * lines either side — enough context to see where it begins and ends, and what it follows — and scrolls when the
	 * statement is longer than that, rather than shrinking the page until nothing can be read.
	 */
	let statement = $state<{ page: number; rects: number[][] } | null>(null);
	$effect(() => {
		const t = target;
		statement = null;
		if (!t || t.kind !== 'work' || !t.result || !ref?.spans) return;
		let dropped = false;
		fetch(dataUrl(ref.spans.path))
			.then((r) => (r.ok ? (r.json() as Promise<Sidecar>) : null))
			.then((j) => {
				const rects = j?.quads?.[t.result!];
				if (!dropped && rects?.length) statement = { page: t.link.page ?? 1, rects };
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	/**
	 * How large the page is drawn inside the card, and how tall the card then is.
	 *
	 * The card is a window `CARD_WIDTH` wide (`.page-card` below), and the page is drawn at 115% of it: a paper's
	 * margins are not what the reader hovered, so letting them fall outside the window buys back the width that the
	 * text is read at. `PAGE_WIDTH` is US Letter, which every paper in the fixture is; a page of another size shifts
	 * the zoom a little either way, which is what the fixed scale here has always done.
	 */
	const CARD_WIDTH = 43.2 * 16;
	const PAGE_WIDTH = 612;
	const CARD_SCALE = (CARD_WIDTH * 1.15) / PAGE_WIDTH;
	/** The card's height: the statement and two lines either side, in points at the card's own scale. */
	const cropHeight = $derived.by(() => {
		const rs = statement?.rects ?? [];
		if (!rs.length) return 0;
		const top = Math.min(...rs.map((r) => r[1]));
		const bottom = Math.max(...rs.map((r) => r[3]));
		const line = Math.max(...rs.map((r) => r[3] - r[1]));
		return Math.round((bottom - top + line * 4) * CARD_SCALE);
	});
	$effect(() => {
		const t = target;
		lit = null;
		if (!t || t.kind !== 'work') return;
		const at = t.link.page ?? 1;
		if (t.link.box) {
			lit = { page: at, rects: [[...t.link.box]] };
			return;
		}
		if (!t.link.span && !t.link.quote) return;
		let dropped = false;
		void can('locate').then((ok) => {
			if (!ok || dropped) return;
			const body = t.link.span ? { citekey: t.citekey, page: at, span: t.link.span } : { citekey: t.citekey, page: at, text: t.link.quote };
			return write('locate', body).then((res: WriteResult & { anchor?: { quads?: number[][] } }) => {
				if (!dropped && res.ok && res.anchor?.quads?.length) lit = { page: at, rects: res.anchor.quads };
			});
		});
		return () => {
			dropped = true;
		};
	});
	const number = $derived.by(() => {
		if (!node || !m) return '';
		const master = m.masters.find((x) => x.default)?.path ?? '';
		return node.numbers[master]?.number ?? '';
	});

	/** What a link points at, if it is something a card can show. An SVG link (a node in a graph drawing) names its node directly, since it has no `pathname`. */
	function resolve(a: Element): Target | null {
		if (!m || a.closest('.link-preview, [data-no-preview]')) return null;
		const owner = (key: string) => {
			const region = m.regions[key];
			const k = region ? region.container : key;
			const n = m.keys[k]?.node ?? k;
			return m.nodes[n] ? n : null;
		};
		/**
		 * A node's preview.
		 *
		 * **A digest node previews the paper, not the digest.** A result read off a cited work is a transcription of a
		 * page, and a reader hovering a citation wants the page — the digest's rendering of it, its badges and its
		 * provenance are what the work's own tabs are for. With no copy filed, or no page in the locator, the
		 * transcription is the best there is and stands.
		 */
		const preview = (n: string): Target => {

			// deliberately not named `node` or `ref`: both are `$derived` in this component, and a local of the same
			// name inside a nested function is a trap worth not setting
			const nd = m.nodes[n];
			const ck = nd?.digest;
			const work = ck ? m.references[ck] : undefined;
			const at = pageOf(nd?.locator);
			if (work?.artifacts?.pdf && at) {
				return { kind: 'work', citekey: work.citekey, link: { id: work.work ?? work.citekey, page: at }, url: artifactUrl(work.artifacts.dir), result: n };
			}
			return { kind: 'node', key: n };
		};
		const named = a.getAttribute('data-preview-key');
		if (named) {
			const n = owner(named);
			return n ? preview(n) : null;
		}
		const href = a.getAttribute('href');
		if (isWorkLink(href)) {
			const link = parseWorkLink(href!);
			const where = link ? locate(m, link) : undefined;
			if (!link || !where?.ref) return null;
			// the very artifact the link names, on this machine: the page at the place, not the record
			if (where.local && where.ref.artifacts?.pdf) return { kind: 'work', citekey: where.ref.citekey, link, url: artifactUrl(where.ref.artifacts.dir) };
			return null;
		}
		const refTarget = a.matches('a.ref[data-target]') ? a.getAttribute('data-target') : a.closest<HTMLElement>('span.cite[data-target]')?.dataset.target;
		if (refTarget) {
			const n = owner(refTarget);
			return n ? preview(n) : null;
		}
		const url = new URL(a.getAttribute('href') ?? '', location.href);
		if (url.origin !== location.origin) return null;
		const path = url.pathname;
		if (path.startsWith('/node/')) {
			const n = owner(keyFromParam(path.slice('/node/'.length)));
			// a link to the page already open previews nothing a reader cannot already see
			if (!n || page.url.pathname === path) return null;
			return preview(n);
		}
		if (path.startsWith('/library/')) {
			const ck = decodeURIComponent(path.slice('/library/'.length));
			const r = m.references[ck];
			if (!r || page.url.pathname === path) return null;
			// the page itself when a copy is filed, at whatever place the URL names; otherwise nothing to show
			if (!r.artifacts?.pdf) return null;
			const link = readKeys({ id: r.work ?? ck }, url.search.slice(1));
			// A citation carrying a postnote names a place, not a work. Where the postnote is a digest node, `refTarget`
			// above already previewed it; reaching here means it is not one, and the postnote is all there is to go on.
			// It is often enough -- an author writes `\cite[Corollary 3.2, p.~2]{Arden24}` and the page is right there.
			// Where it names no page, the place is unknown, and the honest preview of an unknown place is none: a card
			// for the front page would answer a question nobody asked, showing `[1, Lemma 5.9]` the title and the
			// abstract as though they were the lemma. A bare `\cite{Arden24}` names the work, so its front page stands.
			const postnote = a.closest<HTMLElement>('span.cite')?.dataset.postnote;
			if (!link.page && postnote) {
				const at = pageOf(postnote);
				if (!at) return null;
				link.page = at;
			}
			return { kind: 'work', citekey: ck, link, url: artifactUrl(r.artifacts.dir) };
		}
		return null;
	}

	function hide() {
		clearTimeout(showTimer);
		clearTimeout(hideTimer);
		target = null;
		html = '';
		anchor = null;
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

	/** Start fetching a node's fragment while the pointer waits out the delay, so the card's body is on hand when it opens rather than a request later. `fetchFragment` caches per manifest, so `show` gets the same promise. */
	function prefetch(t: Target) {
		const n = t.kind === 'node' ? m?.nodes[t.key] : undefined;
		if (n && n.kind !== 'section') void fetchFragment(n.fragment, store.hash).catch(() => '');
	}

	async function show(a: Element, t: Target) {
		if (!m) return;
		anchor = a;
		target = t;
		html = '';
		void place();
		if (t.kind !== 'node') return;
		const n = m.nodes[t.key];
		// a section's fragment is the whole section, which is too much to fetch and typeset for a glance; its title and state say enough
		if (!n || n.kind === 'section') return;
		const text = await fetchFragment(n.fragment, store.hash).catch(() => '');
		if (target !== t) return;
		html = text;
		await tick();
		if (!body || target !== t) return;
		wire(body, m, () => {});
		const sets = m.macros.sets ?? {};
		await typeset(body, m.macros.default ?? [], n.digest ? (sets[n.digest] ?? []) : []);
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
			const t = resolve(a);
			if (!t) return;
			pending = a;
			prefetch(t);
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

{#if target && m && (node || ref)}
	<div class="link-preview" class:page={target.kind === 'work'} role="tooltip" bind:this={card} style="left: {left}px; top: {top}px" data-testid="link-preview">
		{#if node}
			<p class="head">
				<span class="label">{node.taxon}{number ? ' ' + number : ''}</span>
				{#if node.title}<span class="title"><Tex text={node.title} /></span>{/if}
				<span class="id">{node.id}</span>
			</p>
			<p class="state"><Badge parts={nodeBadge(m, node)} />{#if node.external && node.digest}<span class="from">from {node.digest}{node.locator ? ', ' + node.locator : ''}</span>{/if}</p>
			{#if node.kind === 'section'}
				{#if node.children.length}<p class="more">{node.children.length} {node.children.length === 1 ? 'entry' : 'entries'} in this section</p>{/if}
			{:else}
				<div class="body fragment" bind:this={body}>{@html html}</div>
			{/if}
		{:else if target.kind === 'work' && ref}
			<!-- Sized to the statement and a line either side where the sidecar knows where it is, and scrolled to it by
			     the renderer's own `focus`; a statement longer than the card scrolls inside it rather than being shrunk
			     until it cannot be read. A work with no located statement keeps the standing page-sized card. -->
			<div
				class="page-card"
				class:cropped={!!statement}
				style={statement ? `height: ${Math.min(cropHeight, 39.6 * 16)}px` : undefined}
				data-testid="preview-page"
			>
				<PdfDoc
					url={target.url}
					page={statement?.page ?? target.link.page ?? 1}
					toolbar={false}
					scale={statement ? CARD_SCALE : 0.99}
					window={0}
					spans={statement
						? [{ id: '_stmt', page: statement.page, rects: statement.rects, transient: true }]
						: lit
							? [{ id: '_locator', page: lit.page, rects: lit.rects, transient: true }]
							: []}
					focus={statement ? '_stmt' : lit ? '_locator' : ''}
				/>
			</div>
		{/if}
	</div>
{/if}

<style>
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
	p {
		margin: 0;
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 var(--gap-tight);
	}
	.label {
		font-weight: 500;
		color: var(--ink);
	}
	.title {
		font-family: var(--body-face);
		font-size: 13px;
		color: var(--ink);
	}
	.id {
		margin-left: auto;
		font-family: var(--mono);
		font-size: 9px;
		color: var(--link);
	}
	.state {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--gap-tight);
		margin: var(--gap-hair) 0;
	}
	.from,
	.more {
		color: var(--ink-faint);
		font-size: 10px;
	}
	/* Clamped by height with a fade rather than by truncating the text, which could split a formula; the fade reads as continuing rather than ending. */
	.body {
		max-height: 12rem;
		overflow: hidden;
		-webkit-mask-image: linear-gradient(to bottom, #000 9rem, transparent);
		mask-image: linear-gradient(to bottom, #000 9rem, transparent);
		font-size: 12.5px;
	}
	.body :global(.env) {
		margin: 0;
	}
	/* the card's own header already names the result, and a proof is not what a glance is for */
	.body :global(details.env-proof),
	.body :global(.node-margin),
	.body :global(a.heading-link),
	.body :global(.env > .env-label) {
		display: none;
	}
	.body :global(.math.display) {
		background: none;
	}
	/* the page at the place: a fixed-size window onto the renderer, at a scale a glance can read */
	.page-card {
		width: 43.2rem;
		height: 28.8rem;
		overflow: hidden;
		background: var(--sheet);
	}
	/**
	 * A page preview is the page and nothing else, so the card is the frame: no padding around it and no border of its
	 * own. The two used to sit one inside the other -- the card's rule a few pixels in from the tooltip's -- which read
	 * as a box in a box for the sake of a boundary already drawn. The radius is inherited and clipped so the page takes
	 * the corners.
	 */
	.link-preview.page {
		padding: 0;
		overflow: hidden;
		max-width: min(46.8rem, calc(100vw - 16px));
	}
	/* **The card marks where the result starts; it does not outline it.** The statement's rectangles are what the card
	   is sized and scrolled by, but drawing them boxes three lines of a paper the reader is trying to read. A dot in
	   the margin beside the first line says the same thing — this is where it begins — and leaves the text alone. */
	.page-card :global(.mark.transient) {
		outline: none;
		background: none;
	}
	.page-card :global(.marks > .mark.transient:first-child)::before {
		content: '';
		position: absolute;
		left: -0.7em;
		top: 50%;
		width: 0.5em;
		height: 0.5em;
		transform: translateY(-50%);
		border-radius: 50%;
		background: rgb(224 168 32 / 0.55);
	}
	/* the height comes from the statement; the floor keeps a one-line result from being a sliver */
	.page-card.cropped {
		min-height: 9rem;
		max-height: 39.6rem;
	}
	@media (hover: none) {
		.link-preview {
			display: none;
		}
	}
</style>
