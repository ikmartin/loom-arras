// A document's versions as Review › Record and a version's toolbar read them: each labelled by the act it was kept at, oldest first; and every act of the history said in words. Model facts in, display facts out.
import type { CanonDoc, HistoryAct, Manifest } from '$lib/manifest/types';

const file = (p: string) => p.split('/').pop() ?? p;

/** What a version is called: the act it was kept at in the person's words (the step's message), "Imported" for the paper as received, else its name. */
export function versionLabel(c: CanonDoc): string {
	if (c.action === 'import') return 'Imported';
	return c.message || c.name || c.stem;
}

/** The versions of a live document, oldest first. */
export function versionsOf(m: Pick<Manifest, 'canon'>, doc: string): CanonDoc[] {
	return (m.canon ?? []).filter((c) => c.in === doc).sort((a, b) => Number(a.step ?? 0) - Number(b.step ?? 0));
}

/** The version before and after `path` among its document's, or null at either end; after the newest comes the live text, which the caller names. */
export function neighbours(m: Pick<Manifest, 'canon'>, path: string): { older: CanonDoc | null; newer: CanonDoc | null; doc: string } | null {
	const c = (m.canon ?? []).find((x) => x.path === path);
	if (!c?.in) return null;
	const all = versionsOf(m, c.in);
	const i = all.findIndex((x) => x.path === path);
	return { older: all[i - 1] ?? null, newer: all[i + 1] ?? null, doc: c.in };
}

/** Who recorded the step a version was kept at, as the history names them. */
export function versionActor(m: Pick<Manifest, 'history'>, c: CanonDoc): string {
	return m.history?.steps.find((s) => s.landmark === c.path)?.actor ?? '';
}

/** Whether an act is a version a timeline already shows for the act beside it (a keep's, an undo's, a restore's), and so not listed again. */
function beside(a: HistoryAct): boolean {
	return a.action === 'stamp' && !!a.kept_for && ['keep', 'undo', 'restore'].includes(a.kept_for);
}

/** How much of a file an act took: one change, several, or the edit as a whole. */
const changesWord = (a: HistoryAct) => (!a.hunks ? 'an edit' : a.hunks.length === 1 ? 'one change' : `${a.hunks.length} changes`);

/** What an act was, in words: "Kept an edit to intro.tex", "Undid an edit to README.md", "Recorded the version “Before referee” of main.tex"… An act loom does not know is said by its name. */
export function actWords(a: HistoryAct): string {
	const of = a.in ? ` of ${file(a.in)}` : '';
	switch (a.action) {
		case 'keep':
			return a.path ? `Kept ${changesWord(a)} to ${file(a.path)}` : `Kept every change (${a.paths?.length ?? 0} files)`;
		case 'undo':
			return a.to === undefined || a.to === null ? `Removed the new file ${file(a.path ?? '')}, keeping its text` : `Undid ${changesWord(a)} to ${file(a.path ?? '')}`;
		case 'restore':
			return a.path ? `Put back in ${file(a.path)} the text an undo set aside` : `Put ${file(a.in ?? '')} back as a version`;
		case 'import':
			return `Imported the paper${a.in ? ` as ${file(a.in)}` : ''}`;
		case 'stamp':
			if (a.kept_for === 'adopt' || a.kept_for === 'sync') return `Kept a version${of} first: ${a.message ?? ''}`.trim();
			return a.landmark ? `Recorded the version “${a.message ?? ''}”${of}` : `Recorded the whole quilt: ${a.message ?? ''}`;
		case 'copy':
			return `Made an agent's copy${a.in ? ` of ${file(a.in)}` : ''}`;
		case 'adopt':
			return `Took changes in from the copy ${file(a.copy ?? '')}`;
		case 'draft-close':
			return `Closed the agent's copy ${file(a.copy ?? '')}`;
		case 'draft-reopen':
			return `Reopened the agent's copy ${file(a.copy ?? '')}`;
		case 'live':
			return `Brought ${file(a.path ?? '')} back into the quilt`;
		case 'page-write':
			return `Wrote the page ${a.page ?? file(a.path ?? '')}`;
		case 'move': {
			// a move between folders keeps its file name, so each end is said by its path
			const [from, to] = [a.from ?? '', a.to ?? ''];
			return file(from) === file(to) ? `Moved ${from} to ${to}` : `Moved ${file(from)} to ${file(to)}`;
		}
		default:
			return a.action.replaceAll('-', ' ');
	}
}

/** The acts Review › Record lists, newest first; with `doc`, only those about it or one of the files it is made of (`files`). */
export function actsOf(m: Pick<Manifest, 'history'>, doc = '', files: Set<string> = new Set()): HistoryAct[] {
	const acts = (m.history?.acts ?? []).filter((a) => !beside(a));
	const mine = doc ? acts.filter((a) => a.in === doc || (a.path && files.has(a.path)) || (a.paths ?? []).some((p) => files.has(p))) : acts;
	return [...mine].reverse();
}

/** The files a live document is made of, as the manifest knows them: the document and each file a block it reaches stands in. */
export function filesOf(m: Pick<Manifest, 'nodes'>, doc: string): Set<string> {
	const out = new Set([doc]);
	for (const n of Object.values(m.nodes)) if (n.file && n.reached_by.includes(doc)) out.add(n.file);
	return out;
}
