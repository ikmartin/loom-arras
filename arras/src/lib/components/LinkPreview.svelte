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
	import { isWorkLink, locate, parseWorkLink } from '$lib/worklink';
	import Badge from './Badge.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from './WorkLinks.svelte';

	const SHOW_MS = 300;
	const HIDE_MS = 200;

	type Target = { kind: 'node'; key: string } | { kind: 'ref'; citekey: string };

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
	const ref = $derived(m && target?.kind === 'ref' ? m.references[target.citekey] : undefined);
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
		const named = a.getAttribute('data-preview-key');
		if (named) {
			const n = owner(named);
			return n ? { kind: 'node', key: n } : null;
		}
		const href = a.getAttribute('href');
		if (isWorkLink(href)) {
			const link = parseWorkLink(href!);
			const found = link ? locate(m, link).ref : undefined;
			return found ? { kind: 'ref', citekey: found.citekey } : null;
		}
		const refTarget = a.matches('a.ref[data-target]') ? a.getAttribute('data-target') : a.closest<HTMLElement>('span.cite[data-target]')?.dataset.target;
		if (refTarget) {
			const n = owner(refTarget);
			return n ? { kind: 'node', key: n } : null;
		}
		const url = new URL(a.getAttribute('href') ?? '', location.href);
		if (url.origin !== location.origin) return null;
		const path = url.pathname;
		if (path.startsWith('/node/')) {
			const n = owner(keyFromParam(path.slice('/node/'.length)));
			// a link to the page already open previews nothing a reader cannot already see
			if (!n || page.url.pathname === path) return null;
			return { kind: 'node', key: n };
		}
		if (path.startsWith('/digest/')) {
			const ck = decodeURIComponent(path.slice('/digest/'.length));
			return m.references[ck] && page.url.pathname !== path ? { kind: 'ref', citekey: ck } : null;
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
		const scroll = () => target && hide();
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
	<div class="link-preview" role="tooltip" bind:this={card} style="left: {left}px; top: {top}px" data-testid="link-preview">
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
		{:else if ref}
			<p class="head"><span class="title"><Tex text={bibText(ref.bib.title) || ref.citekey} /></span></p>
			<p class="byline">{bibText(ref.bib.author)}{ref.bib.year ? ` · ${ref.bib.year}` : ''}</p>
			<p class="state"><WorkLinks {ref} />{#if ref.digest}<span class="from">digest of {ref.digest.nodes.length} results</span>{/if}</p>
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
	.byline,
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
	@media (hover: none) {
		.link-preview {
			display: none;
		}
	}
</style>
