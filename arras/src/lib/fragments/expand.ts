// Comments shown where they are (book 15.3.1, the `inline` and `hover` comments preferences): a mark on the text, or a count beside a node that has comments with no mark, opens the comments on it. One is open at a time; selecting outside it or pressing Escape closes it.
//
// Two settings share this controller because they differ only in where the box goes. `inline` puts it in the flow beneath the block the mark sits in, so nothing is covered and the text reflows. `hover` floats it over the page at the mark, free to overlap the text and the gutter, and the pointer opens it; both are dismissed the same way, and in both the box is the same `AnnotationBox`.

import { mount, unmount, type Component } from 'svelte';
import AnnotationBox from '$lib/components/AnnotationBox.svelte';
import { repliesTo } from '$lib/annotations';
import type { Annotation, Manifest } from '$lib/manifest/types';

export interface InlineComments {
	/** Open the comments `ids` beneath `trigger`, or close them when they are already open there. */
	toggle(trigger: HTMLElement, ids: string[]): void;
	close(): void;
	/** The comments the open box shows, or null; a re-wire reads it to open the same comments again. */
	current(): string[] | null;
	destroy(): void;
}

type Box = Component<{ annotation: Annotation; replies: Annotation[]; anchor?: boolean }>;

/** The top-level, undiscarded comments among `ids`; a reply is shown inside its parent, so a mark listing both opens the parent once. */
export function leadComments(manifest: Manifest, ids: string[]): Annotation[] {
	const out: Annotation[] = [];
	const seen = new Set<string>();
	for (const id of ids) {
		let a = manifest.annotations[id];
		while (a?.in_reply_to && manifest.annotations[a.in_reply_to]) a = manifest.annotations[a.in_reply_to];
		if (a && !a.discarded && !seen.has(a.id)) {
			seen.add(a.id);
			out.push(a);
		}
	}
	return out;
}

/** The mark or count in `root` that stands for any of `ids`, so comments open before a re-wire can be opened again after it. */
export function triggerFor(root: HTMLElement, ids: string[]): HTMLElement | null {
	for (const el of root.querySelectorAll<HTMLElement>('mark.annotation[data-annotation], .annotation-block[data-annotation], button.comment-count[data-comments]')) {
		const has = (el.dataset.annotation ?? el.dataset.comments ?? '').split(/\s+/);
		if (ids.some((i) => has.includes(i))) return el;
	}
	return null;
}

export function inlineComments(manifest: Manifest, floating = false): InlineComments {
	let open: { trigger: HTMLElement; host: HTMLElement; made: Record<string, unknown>[]; ids: string[] } | null = null;

	/**
	 * Put a floating box at the mark: below it when there is room, above it when there is not, never off either edge.
	 *
	 * Viewport coordinates and `position: fixed`, so the box does not depend on which ancestor happens to be positioned, and it lives inside the fragment rather than in the page's root -- arras is a guest and writes only in its own subtree. Scrolling closes it, which is what a pointer-opened box should do anyway.
	 */
	const place = (host: HTMLElement, trigger: HTMLElement) => {
		const r = trigger.getBoundingClientRect();
		const width = Math.min(420, window.innerWidth - 32);
		host.style.width = width + 'px';
		host.style.left = Math.min(Math.max(8, r.left), window.innerWidth - width - 8) + 'px';
		host.style.top = r.bottom + 6 + 'px';
		// measured once it is in the page, because its height depends on the comment
		const h = host.offsetHeight;
		if (r.bottom + h + 14 > window.innerHeight && r.top - h - 6 > 0) host.style.top = r.top - h - 6 + 'px';
	};

	const close = () => {
		if (!open) return;
		for (const made of open.made) void unmount(made);
		open.host.remove();
		open.trigger.classList.remove('expanded');
		open.trigger.setAttribute('aria-expanded', 'false');
		open = null;
	};

	const toggle = (trigger: HTMLElement, ids: string[]) => {
		const again = open?.trigger === trigger;
		close();
		if (again) return;
		const lead = leadComments(manifest, ids);
		if (!lead.length) return;
		const host = document.createElement('aside');
		host.className = floating ? 'comment-slot expanded floating' : 'comment-slot expanded';
		host.dataset.testid = 'comment-expanded';
		if (floating) {
			(trigger.closest('.fragment') ?? trigger.parentElement ?? trigger).append(host);
		} else {
			// beneath the paragraph, item or display the mark sits in, so the text keeps its line; a count beside a label opens under the label
			const block = trigger.classList.contains('comment-count')
				? trigger.closest<HTMLElement>('p.env-label, summary.env-label, h1, h2, h3, h4, h5, h6')
				: trigger.closest<HTMLElement>('p, li, .math.display, .annotation-block, summary');
			(block ?? trigger).after(host);
		}
		const made = lead.map(
			(a) =>
				mount(AnnotationBox as unknown as Box, {
					target: host,
					props: { annotation: a, replies: repliesTo(manifest, a.id), anchor: false }
				}) as Record<string, unknown>
		);
		trigger.classList.add('expanded');
		trigger.setAttribute('aria-expanded', 'true');
		open = { trigger, host, made, ids: lead.map((a) => a.id) };
		if (floating) place(host, trigger);
	};

	const down = (e: PointerEvent) => {
		if (!open) return;
		const t = e.target as Element | null;
		if (open.host.contains(t) || t?.closest?.('mark.annotation, .annotation-block, .comment-count')) return;
		close();
	};
	const key = (e: KeyboardEvent) => e.key === 'Escape' && close();
	const away = () => floating && close();
	document.addEventListener('pointerdown', down, true);
	document.addEventListener('keydown', key);
	window.addEventListener('scroll', away, true);
	window.addEventListener('resize', away);

	return {
		toggle,
		close,
		current: () => open?.ids ?? null,
		destroy() {
			close();
			document.removeEventListener('pointerdown', down, true);
			document.removeEventListener('keydown', key);
			window.removeEventListener('scroll', away, true);
			window.removeEventListener('resize', away);
		}
	};
}
