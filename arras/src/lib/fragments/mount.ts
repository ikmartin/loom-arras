// After a fragment is injected: references become routes, images point at the build directory, citations link to their targets, inclusions become links the viewer can expand.
import { anchorId, digestUrl, keyUrl, nodeUrl } from '$lib/nav';
import { toneClass } from '$lib/state';
import type { Manifest } from '$lib/manifest/types';

export interface WireOptions {
	/** The master being read, when the fragment is part of a whole document: a reference to a node the same document reaches becomes an in-page jump rather than a navigation (book 15.3.1). */
	master?: string;
	/** Renders the Stacks-project heading affordance: a node's own link, revealed on hover. Off on a node page, where the heading is already the page. */
	headingLinks?: boolean;
	/** Renders the read view's margin column: the key and its state beside every node (book 15.3.1). */
	margins?: boolean;
	/** Places a slot for each node's comments: in the right gutter when the comment is short, in the flow when it is long (book 15.3.1). The caller fills the slots; this only decides where they go. */
	comments?: (key: string) => CommentPlacement[];
	/** Expands comments in place instead of pointing at a card elsewhere: marks and counts call this with the comments they stand for (the `inline` comments preference). */
	expand?: (trigger: HTMLElement, ids: string[]) => void;
}

/** One comment and where it belongs beside the node it is about. */
export interface CommentPlacement {
	id: string;
	/** `gutter` stands beside the node; `inline` stays in the text as a box; `count` is a small control beside the node's label that expands it, for a comment with no mark of its own when comments are shown in place. */
	where: 'gutter' | 'inline' | 'count';
}

export function labelFor(manifest: Manifest | null, key: string): string {
	const n = manifest?.nodes[key];
	if (!n) return key;
	const num = manifest?.masters.find((m) => m.default)?.path;
	const number = num ? n.numbers[num]?.number : undefined;
	return `${n.taxon}${number ? ' ' + number : ''}${n.title ? ' (' + n.title + ')' : ''}`;
}

export function wire(
	root: HTMLElement,
	manifest: Manifest | null,
	expand: (el: HTMLElement, key: string) => void,
	select: (id: string) => void = () => {},
	opts: WireOptions = {}
): void {
	for (const a of root.querySelectorAll<HTMLAnchorElement>('a.ref[data-target]')) {
		const target = a.dataset.target ?? '';
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
	// A citation with a digest node behind it opens that result; one without opens the reference, which links out to the work. A citekey the manifest does not know stays text.
	for (const c of root.querySelectorAll<HTMLElement>('span.cite[data-citekey]')) {
		if (c.querySelector('a')) continue;
		const target = c.dataset.target;
		const citekey = c.dataset.citekey ?? '';
		const href = target ? nodeUrl(target) : manifest?.references[citekey] ? digestUrl(citekey) : '';
		if (!href) continue;
		const a = document.createElement('a');
		a.href = href;
		a.className = target ? 'cite-link' : 'cite-link cite-work';
		while (c.firstChild) a.appendChild(c.firstChild);
		c.appendChild(a);
	}
	for (const img of root.querySelectorAll<HTMLImageElement>('img[src]')) {
		const src = img.getAttribute('src') ?? '';
		if (!/^(\/|https?:)/.test(src)) img.src = '/build/' + src;
	}
	for (const mark of root.querySelectorAll<HTMLElement>('mark.annotation[data-annotation], .annotation-block[data-annotation]')) {
		if (mark.dataset.wiredMark) continue;
		mark.dataset.wiredMark = '1';
		const ids = (mark.dataset.annotation ?? '').split(/\s+/).filter(Boolean);
		// several comments can share one phrase, and the mark lists them in no particular order; the one to select is the one with a card of its own, since a reply is shown inside its parent
		const lead = ids.find((i) => manifest?.annotations[i] && !manifest.annotations[i].in_reply_to) ?? ids[0] ?? '';
		const first = manifest?.annotations[lead];
		if (first) {
			mark.title = `${first.kind}: ${first.author.label ?? first.author.id}`;
			// coloured by what the comment is, so an objection reads differently from a question before anyone opens it
			mark.classList.add('k-' + first.kind);
		}
		mark.setAttribute('role', 'button');
		mark.setAttribute('tabindex', '0');
		if (opts.expand) mark.setAttribute('aria-expanded', 'false');
		else mark.setAttribute('aria-describedby', ids.map((i) => 'ann-' + i).join(' '));
		const go = () => {
			if (opts.expand) return opts.expand(mark, ids);
			select(lead);
			document.getElementById('ann-' + lead)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
		};
		mark.addEventListener('click', go);
		mark.addEventListener('keydown', (e) => e.key === 'Enter' && go());
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
			const counted = placements.filter((p) => p.where === 'count').map((p) => p.id);
			const label = el.querySelector<HTMLElement>(':scope > p.env-label, :scope > summary.env-label, :scope > :is(h1,h2,h3,h4,h5,h6)');
			if (counted.length && label && opts.expand) {
				const kind = manifest?.annotations[counted[0]]?.kind ?? '';
				const btn = document.createElement('button');
				btn.type = 'button';
				btn.className = `comment-count k-${kind}`;
				btn.textContent = counted.length === 1 ? '1 comment' : `${counted.length} comments`;
				btn.setAttribute('aria-expanded', 'false');
				btn.dataset.countFor = key;
				btn.addEventListener('click', (e) => {
					e.preventDefault(); // inside a proof's summary a click would also fold the proof
					opts.expand!(btn, counted);
				});
				label.appendChild(btn);
			}
			for (const where of ['gutter', 'inline'] as const) {
				const ids = placements.filter((p) => p.where === where).map((p) => p.id);
				if (!ids.length) continue;
				const slot = document.createElement('aside');
				slot.className = `comment-slot ${where}`;
				slot.dataset.commentSlot = ids.join(' ');
				slot.dataset.slotFor = key;
				// a gutter slot is positioned against the node, so it is a child of it; an inline slot is a sibling, because it takes room in the text
				if (where === 'gutter') el.appendChild(slot);
				else el.after(slot);
			}
		}
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
