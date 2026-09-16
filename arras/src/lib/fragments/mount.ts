// After a fragment is injected: references become routes, images point at the build directory, citations link to their targets, inclusions become links the viewer can expand.
import { nodeUrl } from '$lib/nav';
import type { Manifest } from '$lib/manifest/types';

export function labelFor(manifest: Manifest | null, key: string): string {
	const n = manifest?.nodes[key];
	if (!n) return key;
	const num = manifest?.masters.find((m) => m.default)?.path;
	const number = num ? n.numbers[num]?.number : undefined;
	return `${n.taxon}${number ? ' ' + number : ''}${n.title ? ' (' + n.title + ')' : ''}`;
}

export function wire(root: HTMLElement, manifest: Manifest | null, expand: (el: HTMLElement, key: string) => void, select: (id: string) => void = () => {}): void {
	for (const a of root.querySelectorAll<HTMLAnchorElement>('a.ref[data-target]')) {
		const target = a.dataset.target ?? '';
		if (a.classList.contains('ref-dangling')) {
			a.removeAttribute('href');
			a.title = `dangling reference to ${target}`;
			continue;
		}
		const region = manifest?.regions[target];
		a.href = nodeUrl(region ? region.container : target) + (region ? '#' + region.label.replace(/[^A-Za-z0-9]+/g, '-') : '');
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
