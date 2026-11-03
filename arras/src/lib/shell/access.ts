// Who edits a file in the project's tree: only the person, or the person and agents. The publisher says it per file (`ProjectFile.denied`), so the viewer never matches the quilt's deny list itself, and where it says nothing the row has no mark: silence is not permission. This module only gathers a directory's answer from its files and puts each answer in words for the mark's popup.
import type { ProjectFile } from '$lib/manifest/types';

/** One row's answer: whether agents edit it too, and, where they do not, what keeps them out and whether that holds whatever the deny list says. */
export interface Access {
	agents: boolean;
	by?: string;
	always?: boolean;
}

/** What the mark's popup says: its first line, then why. */
export interface Explained {
	title: string;
	body: string;
}

/** The kinds Review › Changes follows, being text a person looks at; a PDF or an image an agent replaces is not shown there. */
const TEXT = new Set(['document', 'tex', 'markdown', 'text', 'html', 'notebook']);

/** A file's answer, or null where its publisher does not say. */
export function accessOf(f: ProjectFile): Access | null {
	if (f.denied === undefined) return null;
	return f.denied ? { agents: false, by: f.denied.by, always: f.denied.always } : { agents: true };
}

/** Whether the publisher says who edits its files at all; an agent's copy is marked only where it does. */
export function says(files: ProjectFile[] | undefined): boolean {
	return !!files?.some((f) => f.denied !== undefined);
}

/**
 * A directory's answer, from every file the tree shows beneath it.
 *
 * Null when its files differ, and then each file says its own, or when any of them is unsaid; a shared reason is kept, so a folder the deny list names says so.
 */
export function accessOfAll(files: ProjectFile[]): Access | null {
	if (!files.length) return null;
	const known = files.map(accessOf);
	if (known.some((a) => a === null)) return null;
	const all = known as Access[];
	if (all.every((a) => a.agents)) return { agents: true };
	if (all.some((a) => a.agents)) return null;
	return all.every((a) => a.by === all[0].by && a.always === all[0].always) ? all[0] : { agents: false };
}

/**
 * The popup's words for a row.
 *
 * `copyOf` names the document an agent's copy was drafted from; `statePath` is the research state's, which agents change only by asking loom to write it. Where the deny list keeps agents out, the words point to Settings, the one place the list changes.
 */
export function explain(a: Access, at: { dir?: boolean; kind?: string; copyOf?: string; statePath?: string }): Explained {
	if (at.copyOf) {
		const of = at.copyOf.slice(at.copyOf.lastIndexOf('/') + 1);
		return { title: 'You and agents edit this copy', body: `An agent's copy of ${of}. What you take from it comes back to ${of} through Review › Incoming.` };
	}
	if (a.agents) {
		if (at.dir) return { title: 'You and agents edit what is in here', body: 'An agent may change any file in this folder. Review › Changes shows what changed in a text file since you last looked, to keep or undo.' };
		return {
			title: 'You and agents edit this',
			body: TEXT.has(at.kind ?? '') ? 'An agent may change this file. Review › Changes shows what changed since you last looked, to keep or undo.' : 'An agent may change or replace this file.'
		};
	}
	const title = at.dir ? 'Only you edit what is in here' : 'Only you edit this';
	if (a.by && a.by === at.statePath) return { title: 'Agents change this only through loom', body: 'No agent edits the research state itself: loom writes what an agent says in it, and records each change.' };
	if (a.always) return { title, body: a.by === 'config.toml' ? "No agent writes the quilt's configuration." : "This is loom's own record, which no agent edits." };
	if (a.by) return { title, body: `${a.by} is on the list of where agents may not write, in Settings › Agents.` };
	return { title, body: 'Every file in here is kept from agents; each one says why.' };
}
