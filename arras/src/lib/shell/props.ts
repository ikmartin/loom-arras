// The one prop set the three arrangements share (book 15.8). Every shell contains the same elements; adding one here means adding it to all three or to none.

import type { Snippet } from 'svelte';
import type { ContentsEntry } from '$lib/contents';
import type { Master } from '$lib/manifest/types';
import type { View } from './views';

export interface ShellProps {
	label: string;
	views: View[];
	currentView: string;
	masters: Master[];
	currentMaster: string;
	contents: ContentsEntry[];
	currentSection: string;
	counts: { nodes: number; errors: number; warnings: number };
	/** Opens the command palette, which is arras's search (book 15.2). */
	search: () => void;
	children: Snippet;
	rail?: Snippet;
}
