// After a fragment is injected: references become routes, images point at the build directory, citations link to their targets, inclusions become links the viewer can expand.
import { anchorId, workUrl, keyUrl, nodeUrl } from '$lib/nav';
import { dataUrl } from '$lib/paths';
import { pageOf } from '$lib/worklink';
import { taxonTone } from '$lib/taxonomy';
import { toneClass } from '$lib/state';
import type { Manifest } from '$lib/manifest/types';
import { travel } from '$lib/travel/travel';
import { visible } from '$lib/sessions/sessions.svelte';

export interface WireOptions {
	/** The master being read, when the fragment is part of a whole document: a reference to a node the same document reaches becomes an in-page jump rather than a navigation (book 15.3.1). */
	master?: string;
	/** Renders the Stacks-project heading affordance: a node's own link, revealed on hover. Off on a node page, where the heading is already the page. */
	headingLinks?: boolean;
	/** Renders the read view's margin column: the key and its state beside every node (book 15.3.1). */
	margins?: boolean;
	/** Where each of a node's annotations without a mark of its own stands (book 15.3.1): as a mark on the node's label, or as a box in the flow that the caller fills. */
	comments?: (key: string) => CommentSlot[];
	/** A fragment with no node identity (a landmark): its references are the publisher's own in-page anchors and must be left alone, and nothing in it is a key to look up. */
	keyless?: boolean;
	/** Expands comments in place instead of pointing at a card elsewhere: a mark calls this with the annotations it stands for (the `inline` and `floating` preferences). */
	expand?: (trigger: HTMLElement, ids: string[]) => void;
	/** Where an opened box stands: over the text, anchored to the mark, rather than in place. Nothing about how it opens. */
	floating?: boolean;
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

/**
 * The options a wired fragment is currently working under.
 *
 * A mark's handlers are bound once and then read this, so changing where comments stand costs a re-wire rather than a re-render. Re-rendering meant re-typesetting: 1,250 formulas and about 800ms of stall for one click in the settings panel.
 */
const LIVE = new WeakMap<HTMLElement, WireOptions>();

/** Take out what the comment setting put in, so `wire` can put the other setting's back without the fragment being rebuilt. A label mark is unwrapped: its words are the label's and go back where they were. */
export function resetComments(root: HTMLElement): void {
	for (const el of root.querySelectorAll('aside.comment-slot')) el.remove();
	for (const mark of root.querySelectorAll<HTMLElement>('mark.annotation-label')) {
		while (mark.firstChild) mark.parentNode?.insertBefore(mark.firstChild, mark);
		mark.remove();
	}
	for (const el of root.querySelectorAll<HTMLElement>('[data-wired-comments]')) delete el.dataset.wiredComments;
}

/** Whether an annotation is settled: resolved or discarded, so its mark is not drawn at rest (book 15.3.1). */
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

export function wire(
	root: HTMLElement,
	manifest: Manifest | null,
	expand: (el: HTMLElement, key: string) => void,
	select: (id: string) => void = () => {},
	opts: WireOptions = {}
): void {
	LIVE.set(root, opts);
	for (const a of root.querySelectorAll<HTMLAnchorElement>('a.ref[data-target]')) {
		const target = a.dataset.target ?? '';
		if (opts.keyless) continue;
		if (a.classList.contains('ref-dangling')) {
			a.removeAttribute('href');
			a.title = `dangling reference to ${target}`;
			continue;
		}
		const region = manifest?.regions[target];
		// the publisher's element ids are `slug(key)`, and a region's key is `container#label`; building the hash from the bare label is why equation references landed on nothing
		const key = region ? region.key : target;
		const owner = region ? region.container : target;
		const here = opts.master ? manifest?.nodes[owner]?.reached_by?.includes(opts.master) : false;
		a.href = here ? '#' + anchorId(key) : keyUrl(manifest, owner) + (region ? '#' + anchorId(key) : '');
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
		env.style.setProperty('--taxon-tone', taxonTone(manifest, env.dataset.taxon));
	}
	for (const img of root.querySelectorAll<HTMLImageElement>('img[src]')) {
		const src = img.getAttribute('src') ?? '';
		if (!/^(\/|https?:)/.test(src)) img.src = dataUrl(src);
	}
	if (opts.margins) {
		for (const el of root.querySelectorAll<HTMLElement>('div.env[data-key], details.env-proof[data-key]')) {
			if (el.dataset.wiredMargin) continue;
			el.dataset.wiredMargin = '1';
			const key = el.dataset.key ?? '';
			const entry = manifest?.keys[key];
			const label = manifest?.states.labels[entry?.state ?? ''];
			const margin = document.createElement('span');
			margin.className = 'node-margin';
			const idEl = document.createElement('a');
			idEl.className = 'mid';
			idEl.href = keyUrl(manifest, key);
			idEl.textContent = el.dataset.id ?? key;
			margin.appendChild(idEl);
			if (entry) {
				const st = document.createElement('span');
				st.className = 'mstate ' + toneClass(label?.color);
				st.textContent = label?.label ?? entry.state;
				margin.appendChild(st);
			}
			el.prepend(margin);
		}
	}
	if (opts.comments) {
		for (const el of root.querySelectorAll<HTMLElement>('div.env[data-key], details.env-proof[data-key], section[data-key], section[data-id]')) {
			if (el.dataset.wiredComments) continue;
			const key = el.dataset.key ?? el.dataset.id ?? '';
			const placements = key ? opts.comments(key) : [];
			if (!placements.length) continue;
			el.dataset.wiredComments = '1';
			// **One annotation, one mark** (15.3.1). An annotation with no mark of its own -- no quote, or one that no longer resolves -- is a mark on the node's label, in its hue, opening its box like any mark; several share one label mark whose box lists them. The label's own words are moved into the mark, so the underline is under them and nothing is added to the text; the heading link a heading carries stays outside it.
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
		// several annotations can share one phrase, and the mark lists them in no particular order; the one to select, and to take the hue from, is an open one with a card of its own, since a reply is shown inside its parent
		const leads = ids.filter((i) => manifest?.annotations[i] && !manifest.annotations[i].in_reply_to);
		const lead = leads.find((i) => !settled(manifest?.annotations[i])) ?? leads[0] ?? ids[0] ?? '';
		const first = manifest?.annotations[lead];
		const judged = (leads.length ? leads : ids).map((i) => manifest?.annotations[i]).filter((a) => !!a);
		for (const c of [...mark.classList]) if (/^(k|s)-/.test(c)) mark.classList.remove(c);
		if (first) {
			mark.title = `${first.kind}: ${first.author.label ?? first.author.id}`;
			mark.classList.add('k-' + first.kind);
			if (first.severity) mark.classList.add('s-' + first.severity);
		}
		mark.classList.toggle('settled', judged.length > 0 && judged.every(settled));
		mark.classList.toggle('hidden', judged.length > 0 && !judged.some((a) => visible(manifest, a)));
		mark.setAttribute('tabindex', inert(mark) ? '-1' : '0');
		if (mark.dataset.wiredMark) continue;
		mark.dataset.wiredMark = '1';
		mark.setAttribute('role', 'button');
		mark.setAttribute('aria-expanded', 'false');
		mark.setAttribute('aria-describedby', ids.map((i) => 'ann-' + i).join(' '));
		const go = (e: Event) => {
			if (inert(mark)) return;
			// inside a proof's summary a click on the label would also fold the proof
			if (mark.classList.contains('annotation-label')) e.preventDefault();
			const now = LIVE.get(root) ?? opts;
			if (now.expand) return now.expand(mark, ids);
			select(lead);
			card(root, lead)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		};
		// A click opens; hovering never does (plan 0.13 §7). The pointer used to open a box after a beat, which made passing over a marked line flash boxes, could not be read without holding the pointer still, and could not be clicked into at all -- a box that appears under the pointer and vanishes when it moves toward the box.
		mark.addEventListener('click', go);
		mark.addEventListener('keydown', (e) => e.key === 'Enter' && go(e));
		// and a double-click travels to the annotation's box, which carries its id (15.3.1): the one open in this pane, else the one the mark opens for it, else whatever else stands for the annotation on screen. Nothing is invented for one with no box here: the notice says so and the pane stays put.
		mark.addEventListener('dblclick', (e) => {
			e.preventDefault();
			if (inert(mark)) return;
			let to = boxFor(root, lead);
			const now = LIVE.get(root) ?? opts;
			if (!to && now.expand) {
				now.expand(mark, ids);
				to = boxFor(root, lead);
			}
			travel(to ?? card(root, lead), mark);
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
		btn.addEventListener('click', () => expand(inc, key));
		inc.append(a, ' ', btn);
	}
}
