// The contents tree of a master, built from the manifest's inclusion tree (book 15.2, 15.4).
// The inclusion tree is the publisher's own record of what appears where, in document order, with files interleaved at the offsets they are included at. Deriving the contents from it rather than from a sort over `nodes` gives true document order, and needs no numbering: an uncompiled corpus still gets a correct contents list.

import type { Manifest, InclusionNode } from './manifest/types';

export interface ContentsEntry {
	key: string;
	title: string;
	number: string;
	/** Indent steps, 0 for a top-level section. */
	depth: number;
	level: number;
}

export const DEFAULT_MAX_LEVEL = 3;

/**
 * Sections of `masterPath` in document order.
 *
 * Order comes from the tree; depth comes from the section's own `level`, because the tree nests everything a section contains beneath it and a `\subsection` following a `\section` is therefore a tree child but an outline sibling one step down either way, while a second `\section` is a tree child and an outline sibling at the same step. `maxLevel` stops the list at a sectioning depth, so `\paragraph` units stay out of the rail while remaining reachable from their node pages. A file included by `\input` is transparent: it contributes nothing of its own, only the sections inside it.
 */
export function contentsOf(m: Manifest, masterPath: string, maxLevel: number = DEFAULT_MAX_LEVEL): ContentsEntry[] {
	const root = m.inclusion?.[masterPath];
	if (!root) return [];
	const out: ContentsEntry[] = [];
	const walk = (children: InclusionNode[], fallback: number): void => {
		for (const child of children) {
			const node = m.nodes[child.key];
			if (node?.kind === 'section') {
				const level = node.level ?? fallback;
				if (level <= maxLevel) {
					out.push({
						key: child.key,
						title: node.title ?? child.key,
						number: node.numbers?.[masterPath]?.number ?? '',
						depth: Math.max(0, level - 1),
						level
					});
				}
				walk(child.children, level + 1);
				continue;
			}
			// not a section: a file container or a nested environment, transparent to the contents
			walk(child.children, fallback);
		}
	};
	walk(root.children, 1);
	return out;
}
