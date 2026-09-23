// The shell's props (book 15.8): what the layout knows about the page and hands to the navigation shell.

import type { Snippet } from 'svelte';
import type { ContentsEntry } from '$lib/contents';
import type { CanonDoc, Master } from '$lib/manifest/types';
import type { Index, View } from './views';

export interface ShellProps {
	label: string;
	views: View[];
	indexes: Index[];
	currentView: string;
	masters: Master[];
	canon: CanonDoc[];
	/** The document the shell is about, by path: a master or a landmark. */
	currentDoc: string;
	/** Whether that document is on screen, so the panel hangs its contents under it; elsewhere no tree is drawn. */
	onDocument: boolean;
	contents: ContentsEntry[];
	currentSection: string;
	/** The publisher's diagnostics, which the problems glyph carries. */
	counts: { errors: number; warnings: number };
	/** Opens the command palette, which is arras's search (book 15.2). */
	search: () => void;
	children: Snippet;
	rail?: Snippet;
	/** The page's own left-panel contents, when it has any: a table page's filters stand where a document's contents would (book 15.4). */
	panel?: Snippet;
	panelLabel?: string;
}
