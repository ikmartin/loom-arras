// The shell's props: what the layout knows about the page and hands to the column.

import type { Snippet } from 'svelte';
import type { ContentsEntry } from '$lib/contents';
import type { CanonDoc, Master } from '$lib/manifest/types';
import type { Index, Primary } from './views';

export interface ShellProps {
	label: string;
	/** Which of the two primary views the page is under. */
	primary: Primary;
	/** Where Docs goes: the reading address (`readingAddress`), `''` when there is nothing to read. */
	docsHref: string;
	/** The development shelf's indexes, which Settings offers. */
	indexes: Index[];
	masters: Master[];
	canon: CanonDoc[];
	/** The document the shell is about, by path: a master or a landmark. */
	currentDoc: string;
	/** Whether that document is on screen, so its row is marked and the Outline is its; elsewhere no outline is drawn. */
	onDocument: boolean;
	contents: ContentsEntry[];
	currentSection: string;
	/** The publisher's diagnostics, which the problems chip carries. */
	counts: { errors: number; warnings: number };
	children: Snippet;
	rail?: Snippet;
	/** The page's own column contents, when it has any: a table page's filters stand where the documents would. */
	panel?: Snippet;
	panelLabel?: string;
}
