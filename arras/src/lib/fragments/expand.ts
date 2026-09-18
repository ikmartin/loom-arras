// Comments shown where they are (book 15.3.1, the `inline` comments preference): a mark on the text, or a count beside a node that has comments with no mark, expands the comments beneath it in the flow. One is open at a time; selecting outside it or pressing Escape closes it.

import { mount, unmount, type Component } from 'svelte';
import AnnotationBox from '$lib/components/AnnotationBox.svelte';
import { repliesTo } from '$lib/annotations';
import type { Annotation, Manifest } from '$lib/manifest/types';

export interface InlineComments {
	/** Open the comments `ids` beneath `trigger`, or close them when they are already open there. */
	toggle(trigger: HTMLElement, ids: string[]): void;
	close(): void;
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

export function inlineComments(manifest: Manifest): InlineComments {
	let open: { trigger: HTMLElement; host: HTMLElement; made: Record<string, unknown>[] } | null = null;

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
		host.className = 'comment-slot expanded';
		host.dataset.testid = 'comment-expanded';
		// beneath the paragraph, item or display the mark sits in, so the text keeps its line; a count beside a label opens under the label
		const block = trigger.classList.contains('comment-count')
			? trigger.closest<HTMLElement>('p.env-label, summary.env-label, h1, h2, h3, h4, h5, h6')
			: trigger.closest<HTMLElement>('p, li, .math.display, .annotation-block, summary');
		(block ?? trigger).after(host);
		const made = lead.map(
			(a) =>
				mount(AnnotationBox as unknown as Box, {
					target: host,
					props: { annotation: a, replies: repliesTo(manifest, a.id), anchor: false }
				}) as Record<string, unknown>
		);
		trigger.classList.add('expanded');
		trigger.setAttribute('aria-expanded', 'true');
		open = { trigger, host, made };
	};

	const down = (e: PointerEvent) => {
		if (!open) return;
		const t = e.target as Element | null;
		if (open.host.contains(t) || t?.closest?.('mark.annotation, .annotation-block, .comment-count')) return;
		close();
	};
	const key = (e: KeyboardEvent) => e.key === 'Escape' && close();
	document.addEventListener('pointerdown', down, true);
	document.addEventListener('keydown', key);

	return {
		toggle,
		close,
		destroy() {
			close();
			document.removeEventListener('pointerdown', down, true);
			document.removeEventListener('keydown', key);
		}
	};
}
