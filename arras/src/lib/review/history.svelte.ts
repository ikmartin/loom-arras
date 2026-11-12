// The person's own annotation writes in this page's life, each kept with the write that undoes it and the write that does it again: Undo and Redo on the toolbar, ⌘Z and ⇧⌘Z. A new annotation or reply is undone by deleting it and done again by restoring what the delete took out; a delete by restoring and deleting again; an edit by an edit back to its type, look and words before; a resolve by reopening. Every annotation write in the viewer goes through here, so there is one record of what can be undone.
//
// A delete also stands at the foot of the window (`DeletedBar`) while it is done, since its mark goes with the annotation; its Undo there undoes that delete, wherever it is in the history.

import { store } from '$lib/manifest/client.svelte';
import type { Annotation, Look } from '$lib/manifest/types';
import { write, type WriteResult } from '$lib/write';
import { plain, typeById } from './annotating.svelte';

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

/** What puts `a` back as it stands now, for the fields `change` touches: its words, its type, and its look, as its type's when it is drawn so, else its own. */
function before(a: Annotation, change: Record<string, unknown>, types: Parameters<typeof typeById>[0]): Record<string, unknown> {
	const back: Record<string, unknown> = {};
	if ('message' in change) back.message = a.body ?? plain(a.body_html);
	if ('type' in change) back.type = a.type;
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
