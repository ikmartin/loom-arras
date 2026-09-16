// After a fragment is injected: references become routes, images point at the build directory, citations link to their targets, inclusions become links the viewer can expand.
import { anchorId, keyUrl, nodeUrl } from '$lib/nav';
import { toneClass } from '$lib/state';
import type { Manifest } from '$lib/manifest/types';

export interface WireOptions {
	/** The master being read, when the fragment is part of a whole document: a reference to a node the same document reaches becomes an in-page jump rather than a navigation (book 15.3.1). */
	master?: string;
	/** Renders the Stacks-project heading affordance: a node's own link, revealed on hover. Off on a node page, where the heading is already the page. */
	headingLinks?: boolean;
	/** Renders the read view's margin column: the key and its state beside every node (book 15.3.1). */
	margins?: boolean;
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
	for (const c of root.querySelectorAll<HTMLElement>('span.cite[data-target]')) {
		const target = c.dataset.target;
		if (!target || c.querySelector('a')) continue;
		const a = document.createElement('a');
		a.href = nodeUrl(target);
		a.className = 'cite-link';
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
		const first = manifest?.annotations[ids[0] ?? ''];
		if (first) mark.title = `${first.kind}: ${first.author.label ?? first.author.id}`;
		mark.setAttribute('role', 'button');
		mark.setAttribute('tabindex', '0');
		mark.setAttribute('aria-describedby', ids.map((i) => 'ann-' + i).join(' '));
		const go = () => {
			select(ids[0] ?? '');
			document.getElementById('ann-' + ids[0])?.scrollIntoView({ block: 'center', behavior: 'smooth' });
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
