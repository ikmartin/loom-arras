// After a fragment is injected: references become routes, images point at the build directory, citations link to their targets, inclusions become links the viewer can expand.
import { anchorId, masterUrl, workUrl, keyUrl, nodeUrl } from '$lib/nav';
import { dataUrl } from '$lib/paths';
import { pageOf } from '$lib/worklink';
import { taxonTone } from '$lib/taxonomy';
import { toneClass } from '$lib/state';
import type { Manifest } from '$lib/manifest/types';
import { travel } from '$lib/travel/travel';
import { visible } from '$lib/sessions/sessions.svelte';

export interface WireOptions {
	/** The master being read, when the fragment is part of a whole document: a reference to a node the same document reaches becomes an in-page jump rather than a navigation. */
	master?: string;
	/** Renders the Stacks-project heading affordance: a node's own link, revealed on hover. Off on a node page, where the heading is already the page. */
	headingLinks?: boolean;
	/** Renders the read view's margin column: the key and its state beside every node. */
	margins?: boolean;
	/** Where each of a node's annotations without a mark of its own stands: as a mark on the node's label, or as a box in the flow that the caller fills. */
	comments?: (key: string) => CommentSlot[];
	/** A fragment with no node identity (a landmark): its references are the publisher's own in-page anchors and must be left alone, and nothing in it is a key to look up. */
	keyless?: boolean;
	/** Expands comments in place instead of pointing at a card elsewhere: a mark calls this with the annotations it stands for (the `inline` and `floating` preferences). */
	expand?: (trigger: HTMLElement, ids: string[]) => void;
	/** Where an opened box stands: over the text, anchored to the mark, rather than in place. Nothing about how it opens. */
	floating?: boolean;
	/** Every annotation hidden, as the pane the fragment stands in asks: its marks read as plain text, and none goes on a label. */
	hide?: boolean;
}

/** One annotation and where it stands beside the node it is about.
 *
 * Named `slot` rather than `placement` because an annotation carries a `placement` of its own, which is a different thing: this is the viewer's layout decision, that the publisher's hint about where a payload's text would go. */
export interface CommentSlot {
	id: string;
	/** `inline` stays in the text as a box the caller fills; `label` is a mark on the node's label, for an annotation with no mark of its own (no quote, or one that no longer resolves), opening its box like any mark. */
	where: 'inline' | 'label';
}

export function labelFor(manifest: Manifest | null, key: string): string {
	const n = manifest?.nodes[key];
	if (!n) return key;
	const num = manifest?.masters.find((m) => m.default)?.path;
	const number = num ? n.numbers[num]?.number : undefined;
	return `${n.taxon}${number ? ' ' + number : ''}${n.title ? ' (' + n.title + ')' : ''}`;
}

/** What a wired root is working under now: its options, the manifest it was wired from, and the two callbacks its elements call. */
interface Live extends WireOptions {
	manifest: Manifest | null;
	select: (id: string) => void;
	include: (el: HTMLElement, key: string) => void;
}

/**
 * Each wired root's current options, by root.
 *
 * A mark's and an inclusion's handlers are bound once and look this up when they fire, from the nearest wired root above them, so a re-wire changes what they do without re-rendering, and markup that outlives the call that wired it — kept through a patch, or moved into a new fragment — still answers to the fragment it is in now.
 */
const LIVE = new WeakMap<HTMLElement, Live>();

/** The nearest wired root at or above `el`, with what it is working under; null outside any. */
function liveAt(el: HTMLElement): { root: HTMLElement; now: Live } | null {
	for (let at: HTMLElement | null = el; at; at = at.parentElement) {
		const now = LIVE.get(at);
		if (now) return { root: at, now };
	}
	return null;
}

/** Set an attribute only when it differs: a wiring pass runs on every new manifest over the whole document, and a write of the same value still makes the browser restyle what it touches. */
function set(el: Element, name: string, value: string): void {
	if (el.getAttribute(name) !== value) el.setAttribute(name, value);
}

/** Of the annotations a mark stands for, the one to select and to take the hue from: an open one with a card of its own, since a reply is shown inside its parent. */
function leadOf(manifest: Manifest | null, ids: string[]): string {
	const leads = ids.filter((i) => manifest?.annotations[i] && !manifest.annotations[i].in_reply_to);
	return leads.find((i) => !settled(manifest?.annotations[i])) ?? leads[0] ?? ids[0] ?? '';
}

/** Take out what the comment setting put in, so `wire` can put the other setting's back without the fragment being rebuilt. A label mark is unwrapped: its words are the label's and go back where they were. */
export function resetComments(root: HTMLElement): void {
	for (const el of root.querySelectorAll('aside.comment-slot')) el.remove();
	for (const mark of root.querySelectorAll<HTMLElement>('mark.annotation-label')) {
		while (mark.firstChild) mark.parentNode?.insertBefore(mark.firstChild, mark);
		mark.remove();
	}
	for (const el of root.querySelectorAll<HTMLElement>('[data-wired-comments]')) delete el.dataset.wiredComments;
}

/** Whether an annotation is settled: resolved or discarded, so its mark is not drawn at rest. */
export function settled(a: { status: string; discarded: boolean } | undefined): boolean {
	return !!a && (a.discarded || a.status !== 'open');
}

/** Whether a mark is not drawn, so it is nothing to click, open or tab to: settled with the settled control off, or excluded by the session filter. */
export function inert(mark: HTMLElement): boolean {
	return mark.classList.contains('hidden') || (mark.classList.contains('settled') && !mark.closest('.show-settled'));
}

/**
 * Where a cited result is in the work itself: its page, and the result whose rectangles the sidecar carries.
 *
 * Empty when no copy is filed or the locator names no page, in which case the caller falls back to the digest node.
 */
/** An annotation's card, looked for in the pane the mark stands in before anywhere else: two open items can both hold a card for one annotation. */
export function card(root: HTMLElement, id: string): HTMLElement | null {
	const scope = root.closest('[data-pane]');
	return scope?.querySelector<HTMLElement>(`[id="ann-${CSS.escape(id)}"]`) ?? document.getElementById('ann-' + id);
}

/** The annotation's box, or the reply inside one, open in the pane the mark stands in; null when none is. A box carries `ann-<id>` wherever it is placed, so this is one query. */
export function boxFor(root: HTMLElement, id: string): HTMLElement | null {
	return (root.closest('[data-pane]') ?? root).querySelector<HTMLElement>(`:is(article.box, article.reply)[id="ann-${CSS.escape(id)}"]`);
}

function atResult(manifest: Manifest | null, node: string): string {
	const nd = manifest?.nodes[node];
	const ck = nd?.digest;
	const ref = ck ? manifest?.references[ck] : undefined;
	const at = pageOf(nd?.locator);
	if (!ref?.artifacts?.pdf || !at) return '';
	return `${workUrl(ref.citekey)}?page=${at}&result=${encodeURIComponent(node)}`;
}

/**
 * Wire a fragment's markup: references, citations, tones, images, margins, comment placements, marks, heading links and inclusions.
 *
 * Every pass re-reads what the manifest decides (hrefs, tones, margin states, mark classes); listeners and inserted elements are added once, flagged on the element.
 */
export function wire(
	root: HTMLElement,
	manifest: Manifest | null,
	expand: (el: HTMLElement, key: string) => void,
	select: (id: string) => void = () => {},
	opts: WireOptions = {}
): void {
	LIVE.set(root, { ...opts, manifest, select, include: expand });
	for (const a of root.querySelectorAll<HTMLAnchorElement>('a.ref[data-target]')) {
		const target = a.dataset.target ?? '';
		if (a.dataset.contextDocument) {
			a.href = masterUrl(a.dataset.contextDocument) + '#' + (a.dataset.contextAnchor ?? '');
			a.title = 'Reference in saved paper context';
			continue;
		}
		if (opts.keyless) continue;
		if (a.classList.contains('ref-dangling')) {
			a.removeAttribute('href');
			set(a, 'title', `dangling reference to ${target}`);
			continue;
		}
		const region = manifest?.regions[target];
		// the publisher's element ids are `slug(key)`, and a region's key is `container#label`; building the hash from the bare label is why equation references landed on nothing
		const key = region ? region.key : target;
		const owner = region ? region.container : target;
		const here = opts.master ? manifest?.nodes[owner]?.reached_by?.includes(opts.master) : false;
		set(a, 'href', here ? '#' + anchorId(key) : keyUrl(manifest, owner) + (region ? '#' + anchorId(key) : ''));
	}
	// **A citation opens the paper, not the transcription of it.** `[1, Proposition 2.1]` means that proposition in that work, so where a copy is filed the link goes to the work at the result: the reader lands on the page they cited, with the statement in view. The digest node's own page renders loom's record of the result -- its LaTeX, its provenance, what depends on it -- which is a thing to go and look at, not what the citation names. With no copy filed, or no page in the locator, that record is the best there is and the link goes there as before; a citation with no digest node behind it opens the reference; a citekey the manifest does not know stays text.
	for (const c of root.querySelectorAll<HTMLElement>('span.cite[data-citekey]')) {
		if (c.querySelector('a')) continue;
		const target = c.dataset.target;
		const citekey = c.dataset.citekey ?? '';
		const href = (target ? atResult(manifest, target) : '') || (target ? nodeUrl(target) : manifest?.references[citekey] ? workUrl(citekey) : '');
		if (!href) continue;
		const a = document.createElement('a');
		a.href = href;
		a.className = target ? 'cite-link' : 'cite-link cite-work';
		while (c.firstChild) a.appendChild(c.firstChild);
		c.appendChild(a);
	}
	// One palette, two surfaces: the accent down an environment's edge and the node in the graph are the same colour
	// because both ask `$lib/taxonomy` for it, rather than each keeping a list of taxon names.
	for (const env of root.querySelectorAll<HTMLElement>('.env[data-taxon]')) {
		const tone = taxonTone(manifest, env.dataset.taxon);
		if (env.style.getPropertyValue('--taxon-tone') !== tone) env.style.setProperty('--taxon-tone', tone);
	}
	for (const img of root.querySelectorAll<HTMLImageElement>('img[src]')) {
		const src = img.getAttribute('src') ?? '';
		if (!/^(\/|https?:)/.test(src)) img.src = dataUrl(src);
	}
	if (opts.margins) {
		// read again on every pass, since a node's state moves with the manifest; the margin is made once and changed only where it differs
		for (const el of root.querySelectorAll<HTMLElement>('div.env[data-key], details.env-proof[data-key]')) {
			const key = el.dataset.key ?? '';
			const entry = manifest?.keys[key];
			const label = manifest?.states.labels[entry?.state ?? ''];
			let margin = el.querySelector<HTMLElement>(':scope > span.node-margin');
			if (!margin) {
				margin = document.createElement('span');
				margin.className = 'node-margin';
				const idEl = document.createElement('a');
				idEl.className = 'mid';
				idEl.textContent = el.dataset.id ?? key;
				margin.appendChild(idEl);
				el.prepend(margin);
			}
			set(margin.querySelector<HTMLElement>('a.mid')!, 'href', keyUrl(manifest, key));
			let st = margin.querySelector<HTMLElement>('span.mstate');
			if (!entry) {
				st?.remove();
				continue;
			}
			if (!st) {
				st = document.createElement('span');
				margin.appendChild(st);
			}
			set(st, 'class', 'mstate ' + toneClass(label?.color));
			const text = label?.label ?? entry.state;
			if (st.textContent !== text) st.textContent = text;
		}
	}
	if (opts.comments) {
		for (const el of root.querySelectorAll<HTMLElement>('div.env[data-key], details.env-proof[data-key], section[data-key], section[data-id]')) {
			if (el.dataset.wiredComments) continue;
			const key = el.dataset.key ?? el.dataset.id ?? '';
			const placements = key && !opts.hide ? opts.comments(key) : [];
			if (!placements.length) continue;
			el.dataset.wiredComments = '1';
			// **One annotation, one mark**. An annotation with no mark of its own -- no quote, or one that no longer resolves -- is a mark on the node's label, in its hue, opening its box like any mark; several share one label mark whose box lists them. The label's own words are moved into the mark, so the underline is under them and nothing is added to the text; the heading link a heading carries stays outside it.
			const onLabel = placements.filter((p) => p.where === 'label').map((p) => p.id);
			const label = el.querySelector<HTMLElement>(':scope > p.env-label, :scope > summary.env-label, :scope > :is(h1,h2,h3,h4,h5,h6)');
			if (onLabel.length && label && !label.querySelector('mark.annotation-label')) {
				const mark = document.createElement('mark');
				mark.className = 'annotation annotation-label';
				mark.dataset.annotation = onLabel.join(' ');
				mark.dataset.labelFor = key;
				for (const child of [...label.childNodes]) if (!(child instanceof Element && child.classList.contains('heading-link'))) mark.appendChild(child);
				label.prepend(mark);
			}
			const inline = placements.filter((p) => p.where === 'inline').map((p) => p.id);
			if (inline.length) {
				// a sibling of the node, because it takes room in the text rather than standing beside it
				const slot = document.createElement('aside');
				slot.className = 'comment-slot inline';
				slot.dataset.commentSlot = inline.join(' ');
				slot.dataset.slotFor = key;
				el.after(slot);
			}
		}
	}
	// Every mark, the publisher's and the label marks made above. What a mark looks like is CSS keyed on its classes (theme.css, 15.3.1): `k-<kind>` for the hue, `s-<severity>` for the weight, `settled` for one whose annotation is resolved or discarded, `hidden` for one the session filter excludes. The classes are read from the manifest on every wire, since a resolve or a filter change lands here without the fragment being rebuilt; the handlers are bound once.
	for (const mark of root.querySelectorAll<HTMLElement>('mark.annotation[data-annotation], .annotation-block[data-annotation]')) {
		const ids = (mark.dataset.annotation ?? '').split(/\s+/).filter(Boolean);
		// several annotations can share one phrase, and the mark lists them in no particular order
		const leads = ids.filter((i) => manifest?.annotations[i] && !manifest.annotations[i].in_reply_to);
		const lead = leadOf(manifest, ids);
		const first = manifest?.annotations[lead];
		const judged = (leads.length ? leads : ids).map((i) => manifest?.annotations[i]).filter((a) => !!a);
		// a block mark answers every rule a phrase's does: its hue, its weight, settled and hidden are all keyed on `.annotation`
		const want = new Set(['annotation']);
		if (first) {
			set(mark, 'title', `${first.kind}: ${first.author.label ?? first.author.id}`);
			want.add('k-' + first.kind);
			if (first.severity) want.add('s-' + first.severity);
		}
		if (judged.length > 0 && judged.every(settled)) want.add('settled');
		if (judged.length > 0 && (opts.hide || !judged.some((a) => visible(manifest, a)))) want.add('hidden');
		for (const c of [...mark.classList]) if (/^(k|s)-|^(settled|hidden)$/.test(c) && !want.has(c)) mark.classList.remove(c);
		for (const c of want) if (!mark.classList.contains(c)) mark.classList.add(c);
		set(mark, 'tabindex', inert(mark) ? '-1' : '0');
		if (mark.dataset.wiredMark) continue;
		mark.dataset.wiredMark = '1';
		mark.setAttribute('role', 'button');
		mark.setAttribute('aria-expanded', 'false');
		mark.setAttribute('aria-describedby', ids.map((i) => 'ann-' + i).join(' '));
		const go = (e: Event) => {
			if (inert(mark)) return;
			// inside a proof's summary a click on the label would also fold the proof
			if (mark.classList.contains('annotation-label')) e.preventDefault();
			const at = liveAt(mark);
			if (!at) return;
			if (at.now.expand) return at.now.expand(mark, ids);
			const lead = leadOf(at.now.manifest, ids);
			at.now.select(lead);
			card(at.root, lead)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		};
		// A click opens; hovering never does (plan 0.13 §7). The pointer used to open a box after a beat, which made passing over a marked line flash boxes, could not be read without holding the pointer still, and could not be clicked into at all -- a box that appears under the pointer and vanishes when it moves toward the box.
		mark.addEventListener('click', go);
		mark.addEventListener('keydown', (e) => e.key === 'Enter' && go(e));
		// and a double-click travels to the annotation's box, which carries its id: the one open in this pane, else the one the mark opens for it, else whatever else stands for the annotation on screen. Nothing is invented for one with no box here: the notice says so and the pane stays put.
		mark.addEventListener('dblclick', (e) => {
			e.preventDefault();
			if (inert(mark)) return;
			const at = liveAt(mark);
			if (!at) return;
			const lead = leadOf(at.now.manifest, ids);
			let to = boxFor(at.root, lead);
			if (!to && at.now.expand) {
				at.now.expand(mark, ids);
				to = boxFor(at.root, lead);
			}
			travel(to ?? card(at.root, lead), mark);
		});
	}
	if (opts.headingLinks) {
		for (const el of root.querySelectorAll<HTMLElement>('section[data-id] > :is(h1,h2,h3,h4,h5,h6), div.env[data-id] > p.env-label')) {
			if (el.dataset.wiredHead) continue;
			el.dataset.wiredHead = '1';
			const key = (el.parentElement as HTMLElement | null)?.dataset.id ?? '';
			if (!key) continue;
			const a = document.createElement('a');
			a.className = 'heading-link';
			a.href = keyUrl(manifest, key);
			a.textContent = '¶';
			a.title = key;
			a.setAttribute('aria-label', `the page for ${key}`);
			el.appendChild(a);
		}
	}
	for (const inc of root.querySelectorAll<HTMLElement>('div.include[data-key]')) {
		if (inc.dataset.wired) continue;
		inc.dataset.wired = '1';
		const key = inc.dataset.key ?? '';
		const a = document.createElement('a');
		a.href = nodeUrl(key);
		a.textContent = labelFor(manifest, key);
		const btn = document.createElement('button');
		btn.type = 'button';
		btn.textContent = 'show';
		btn.addEventListener('click', () => liveAt(inc)?.now.include(inc, key));
		inc.append(a, ' ', btn);
	}
}
