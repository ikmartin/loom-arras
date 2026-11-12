// The person's own annotation writes in this page's life, each kept with the write that undoes it and the write that does it again: Undo and Redo on the toolbar, ⌘Z and ⇧⌘Z. A new annotation or reply is undone by deleting it and done again by restoring what the delete took out; a delete by restoring and deleting again; an edit by an edit back to its type, look and words before; a resolve by reopening. Every annotation write in the viewer goes through here, so there is one record of what can be undone.
//
// Keep and Discard of pending changes go through here too, from the document and from Review alike, and are shown so at once (`acted.svelte.ts`). A discarded suggestion is undone by `change-discard` with `undo`, which opens it again. A discarded edit in the file has the person's words written back, a version kept first, and comes back from that version in The Record rather than from here; a keep writes the person's text, and is not undone here either. Neither enters the history.
//
// A delete also stands at the foot of the window (`DeletedBar`) while it is done, since its mark goes with the annotation; its Undo there undoes that delete, wherever it is in the history.

import { store } from '$lib/manifest/client.svelte';
import type { Annotation, Look } from '$lib/manifest/types';
import { write, type WriteResult } from '$lib/write';
import { plain, typeById } from './annotating.svelte';
import { mark, prune, unmark } from './acted.svelte';
import { changesIn, pending } from './changes';
import { say } from './toasts.svelte';

type Events = Record<string, unknown>[];

interface Step {
	/** What it did, as a reader names it: `delete`, `edit`, `resolve`, `new annotation`. */
	label: string;
	undo: () => Promise<WriteResult>;
	redo: () => Promise<WriteResult>;
	/** For a delete, the annotation and the words naming what went, so the foot of the window can offer it. */
	deleted?: { id: string; said: string };
}

/** A delete held at the foot of the window while it stands. */
export interface Deletion {
	id: string;
	said: string;
}

/** The steps are kept raw, never proxied, so a step is the same object in every list that holds it. */
class History {
	done = $state.raw<Step[]>([]);
	undone = $state.raw<Step[]>([]);
	busy = $state(false);
	deletions = $state.raw<Deletion[]>([]);
}

export const history = new History();

async function run(endpoint: string, body: Record<string, unknown>): Promise<WriteResult> {
	const res = await write(endpoint, body);
	if (res.ok) void store.refresh();
	return res;
}

function push(step: Step): void {
	history.done = [...history.done, step];
	history.undone = [];
	if (step.deleted) history.deletions = [...history.deletions, step.deleted];
}

/** The id loom gave a new annotation or reply: the first word of its answer. */
function idOf(res: WriteResult): string {
	return (res.result ?? '').split(/\s+/)[0] ?? '';
}

/** A new annotation or reply `id`: undone by deleting it, done again by restoring exactly what the delete took out. */
function created(id: string, label: string): Step {
	let removed: Events = [];
	return {
		label,
		undo: async () => {
			const res = await run('delete', { annotation: id });
			if (res.ok) removed = res.removed ?? [];
			return res;
		},
		redo: () => run('restore', { events: removed })
	};
}

/**
 * Write a new annotation, kept so it can be undone.
 *
 * Parameters
 * ----------
 * body : object
 *     What `annotate` takes.
 *
 * Returns
 * -------
 * WriteResult
 *     loom's answer; `result` begins with the new annotation's id.
 */
export async function annotate(body: Record<string, unknown>): Promise<WriteResult> {
	const res = await run('annotate', body);
	const id = res.ok ? idOf(res) : '';
	if (id) push(created(id, 'new annotation'));
	return res;
}

/** Reply to annotation `id`, kept so it can be undone. */
export async function reply(id: string, message: string): Promise<WriteResult> {
	const res = await run('reply', { annotation: id, message });
	const made = res.ok ? idOf(res) : '';
	if (made) push(created(made, 'reply'));
	return res;
}

/** What puts `a` back as it stands now, for the fields `change` touches: its words, where a mark on a page stands, its type, and its look, as its type's when it is drawn so, else its own. */
function before(a: Annotation, change: Record<string, unknown>, types: Parameters<typeof typeById>[0]): Record<string, unknown> {
	const back: Record<string, unknown> = {};
	if ('message' in change) back.message = a.body ?? plain(a.body_html);
	if ('type' in change) back.type = a.type;
	if ('rects' in change) back.rects = a.rects ?? [];
	if ('strokes' in change) back.strokes = a.strokes ?? [];
	if ('type' in change || 'look' in change) {
		const t = typeById(types, a.type)?.look;
		back.look = t && sameLook(t, a.look) ? null : { ...a.look };
	}
	return back;
}

/** Whether two looks draw alike. */
export function sameLook(x: Partial<Look>, y: Partial<Look>): boolean {
	return x.color === y.color && x.style === y.style && x.weight === y.weight && x.opacity === y.opacity;
}

/** Edit annotation `a` (`message`, `type`, `look`, a null look dropping its own), kept so it can be undone by an edit back. */
export async function edit(a: Annotation, change: Record<string, unknown>): Promise<WriteResult> {
	const back = before(a, change, store.manifest);
	const res = await run('edit', { annotation: a.id, ...change });
	if (res.ok) push({ label: 'edit', undo: () => run('edit', { annotation: a.id, ...back }), redo: () => run('edit', { annotation: a.id, ...change }) });
	return res;
}

/** Resolve annotation `id`, or with `reopen` open it again, kept so it can be undone by the other. */
export async function resolve(id: string, reopen = false): Promise<WriteResult> {
	const there = () => run('resolve', { annotation: id, ...(reopen ? { undo: true } : {}) });
	const back = () => run('resolve', { annotation: id, ...(reopen ? {} : { undo: true }) });
	const res = await there();
	if (res.ok) push({ label: reopen ? 'reopen' : 'resolve', undo: back, redo: there });
	return res;
}

/** Delete annotation `id` and its replies, kept so it can be undone; '' when it is done, else loom's refusal in its words. */
export async function remove(id: string, said: string): Promise<string> {
	let removed: Events = [];
	const del = async () => {
		const res = await run('delete', { annotation: id });
		if (res.ok) removed = res.removed ?? [];
		return res;
	};
	const res = await del();
	if (!res.ok) return res.error?.message ?? 'the publisher refused it';
	push({ label: 'delete', undo: () => run('restore', { events: removed }), redo: del, deleted: { id, said } });
	return '';
}

/** What `change-keep` and `change-discard` answer: the changes done, by id, and each refused with why. */
export type ChangeAnswer = WriteResult & { done?: string[]; refused?: { id: string; why: string }[] };

/** Which changes an act takes: some by id, or every one, of one document or of the whole quilt. */
export type Which = { changes: string[] } | { all: true; document?: string };

/** The ids `which` names, as the manifest lists them now. */
function idsOf(which: Which): string[] {
	if ('changes' in which) return which.changes;
	const m = store.manifest;
	return (which.document ? changesIn(m, which.document) : pending(m)).filter((c) => c.state === 'ready').map((c) => c.id);
}

/** Act on `which`, shown so at once; what loom refuses, or the whole act when it refuses it, is shown pending again. `suggested` is which of the changes done were suggestions, as the manifest had them. */
async function act(endpoint: 'change-keep' | 'change-discard', which: Which, extra: Record<string, unknown> = {}): Promise<{ res: ChangeAnswer; done: string[]; suggested: string[] }> {
	const asked = idsOf(which);
	const kinds = new Map(pending(store.manifest).map((c) => [c.id, c.kind]));
	mark(asked, endpoint === 'change-keep' ? 'kept' : 'discarded');
	const res = (await write(endpoint, { ...which, ...extra })) as ChangeAnswer;
	const done = res.ok ? (Array.isArray(res.done) ? res.done : asked.filter((id) => !(res.refused ?? []).some((r) => r.id === id))) : [];
	unmark(asked.filter((id) => !done.includes(id)));
	if (res.ok) {
		await store.refresh();
		prune(store.manifest);
	}
	return { res, done, suggested: done.filter((id) => kinds.get(id) === 'suggested') };
}

/**
 * Keep pending changes: an edit in the file becomes what the person has kept, a suggestion is written into its file. Not undone here.
 *
 * Parameters
 * ----------
 * which : Which
 *     Some changes by id, or every one of a document (`document`) or of the quilt.
 *
 * Returns
 * -------
 * ChangeAnswer
 *     loom's answer, with the changes done and each refused.
 */
export async function keepChanges(which: Which): Promise<ChangeAnswer> {
	return (await act('change-keep', which)).res;
}

/**
 * Discard pending changes: an edit in the file has the person's words written back, a version kept first; a suggestion is dropped and the text left as it is, kept so it can be undone.
 *
 * Parameters
 * ----------
 * which : Which
 *     Some changes by id, or every one of a document (`document`) or of the quilt.
 * why : str, optional
 *     Why, kept with a discarded suggestion.
 *
 * Returns
 * -------
 * ChangeAnswer
 */
export async function discardChanges(which: Which, why?: string): Promise<ChangeAnswer> {
	const { res, done, suggested } = await act('change-discard', which, why ? { why } : {});
	// an edit in the file is not undone here: the words it had are in The Record, kept before they were replaced
	const edits = done.length - suggested.length;
	if (edits > 0) say({ title: edits === 1 ? 'Discarded an edit' : `Discarded ${edits} edits`, lines: ['Your words are back in the file. The text it had is kept as a version in The Record.'] });
	if (suggested.length) {
		push({
			label: suggested.length === 1 ? 'discard' : `discard of ${suggested.length} suggestions`,
			undo: async () => {
				const back = await run('change-discard', { changes: suggested, undo: true });
				if (back.ok) unmark(suggested);
				return back;
			},
			redo: async () => (await act('change-discard', { changes: suggested })).res
		});
	}
	return res;
}

/** Take a step back or forward: '' when it is done, else loom's refusal. A delete leaves the foot of the window when undone and comes back when done again. */
async function move(from: 'done' | 'undone', step: Step): Promise<string> {
	if (history.busy) return '';
	history.busy = true;
	const res = from === 'done' ? await step.undo() : await step.redo();
	history.busy = false;
	if (!res.ok) return res.error?.message ?? 'the publisher refused it';
	if (from === 'done') {
		history.done = history.done.filter((s) => s !== step);
		history.undone = [...history.undone, step];
		if (step.deleted) history.deletions = history.deletions.filter((d) => d !== step.deleted);
	} else {
		history.undone = history.undone.filter((s) => s !== step);
		history.done = [...history.done, step];
		if (step.deleted) history.deletions = [...history.deletions, step.deleted];
	}
	return '';
}

/** Undo the last write still done. */
export function undo(): Promise<string> {
	const step = history.done.at(-1);
	return step ? move('done', step) : Promise.resolve('');
}

/** Do again the last write undone. */
export function redo(): Promise<string> {
	const step = history.undone.at(-1);
	return step ? move('undone', step) : Promise.resolve('');
}

/** Undo the delete of annotation `id`, wherever it stands in the history. */
export function undoDelete(id: string): Promise<string> {
	const step = history.done.find((s) => s.deleted?.id === id);
	return step ? move('done', step) : Promise.resolve('');
}

/** Stop offering the undo of a delete at the foot of the window; it can still be undone from the toolbar. */
export function forget(id: string): void {
	history.deletions = history.deletions.filter((d) => d.id !== id);
}

/** What Undo and Redo would do now, for their titles; '' when nothing. */
export function nextUndo(): string {
	return history.done.at(-1)?.label ?? '';
}
export function nextRedo(): string {
	return history.undone.at(-1)?.label ?? '';
}
