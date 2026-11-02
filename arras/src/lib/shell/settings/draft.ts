// The quilt's settings as Settings edits them: the published values, and the changes waiting for Save. A change back to the published value is no change, so the count a reader sees is what Save would write.

import type { QuiltSettings } from '$lib/manifest/types';

export type Value = string | boolean | string[];

/** The published value of every key the publisher lets Settings change, by `table.key`. */
export function published(config: QuiltSettings): Record<string, Value> {
	const out: Record<string, Value> = {};
	for (const key of config.editable) {
		const [table, name] = key.split('.', 2);
		const value = (config as unknown as Record<string, Record<string, unknown>>)[table]?.[name];
		if (typeof value === 'string' || typeof value === 'boolean' || Array.isArray(value)) out[key] = value as Value;
	}
	return out;
}

export function same(a: Value | undefined, b: Value | undefined): boolean {
	if (Array.isArray(a) || Array.isArray(b)) return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => x === b[i]);
	return a === b;
}

/** `edits` with `key` set to `value`, or without it when `value` is what is published. */
export function edited(base: Record<string, Value>, edits: Record<string, Value>, key: string, value: Value): Record<string, Value> {
	const next = { ...edits };
	if (same(base[key], value)) delete next[key];
	else next[key] = value;
	return next;
}

/** `edits` less any that the published values have caught up with, as after a save or an edit to config.toml by hand. */
export function pending(base: Record<string, Value>, edits: Record<string, Value>): Record<string, Value> {
	return Object.fromEntries(Object.entries(edits).filter(([k, v]) => k in base && !same(base[k], v)));
}
