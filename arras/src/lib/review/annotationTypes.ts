// An annotation's type and look, read from the record and the quilt's `annotation_types`.
//
// Nothing here decides by a type's id: what a type means is its record's fields, and an untyped annotation, or one whose type the quilt has since deleted, has none. The look is the annotation's own and is drawn whatever its type now says.

import type { AnnotationType, Look } from '$lib/manifest/types';

/** The nine colours, each a pair of theme.css tokens: `--ann-<colour>` for a line and `--ann-<colour>-band` for a highlight. */
export const COLORS = ['grey', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink'] as const;
export type Color = (typeof COLORS)[number];

export const STYLES = ['underline', 'highlight', 'strike'] as const;

/** Each colour in the light, 0–255, line then band: what a saved PDF copy draws, since a copy has no theme. */
export const RGB: Record<Color, { line: number[]; band: number[] }> = {
	grey: { line: [136, 135, 128], band: [216, 213, 205] },
	brown: { line: [128, 80, 42], band: [215, 178, 135] },
	red: { line: [204, 28, 28], band: [255, 125, 115] },
	orange: { line: [196, 90, 10], band: [255, 190, 120] },
	yellow: { line: [218, 172, 0], band: [255, 235, 60] },
	green: { line: [30, 125, 54], band: [160, 232, 140] },
	blue: { line: [26, 111, 196], band: [140, 205, 255] },
	purple: { line: [116, 67, 204], band: [208, 176, 255] },
	pink: { line: [208, 54, 142], band: [255, 174, 220] }
};

interface Typed {
	annotation_types?: AnnotationType[];
}

/** The type `a` names, while the quilt still has it. */
export function typeOf(m: Typed | null | undefined, a: { type?: string | null }): AnnotationType | undefined {
	return a.type ? m?.annotation_types?.find((t) => t.id === a.type) : undefined;
}

/** The name a list or a label gives `a`: its type's, else `annotation`. */
export function typeName(m: Typed | null | undefined, a: { type?: string | null }): string {
	return typeOf(m, a)?.name ?? 'annotation';
}

/** Whether `a` stays open until resolved: only when its type says so, so an untyped annotation never does. */
export function staysOpen(m: Typed | null | undefined, a: { type?: string | null }): boolean {
	return !!typeOf(m, a)?.open;
}

/** The look's colour when it is one of the nine, else grey. */
export function colorOf(look?: Partial<Look> | null): Color {
	return (COLORS as readonly string[]).includes(look?.color ?? '') ? (look!.color as Color) : 'grey';
}

/** The look's style when it is one of the three, else underline. */
export function styleOf(look?: Partial<Look> | null): Look['style'] {
	return (STYLES as readonly string[]).includes(look?.style ?? '') ? look!.style! : 'underline';
}

/** The CSS variables theme.css draws a mark, a box's stripe and a list's dot from: the colour's two tokens, the weight in whole pixels and the opacity in percent. */
export function lookProps(look?: Partial<Look> | null): Record<string, string> {
	const c = colorOf(look);
	const weight = Math.max(1, Math.round(Number(look?.weight) || 2));
	const opacity = Math.min(100, Math.max(0, Math.round(Number(look?.opacity ?? 100))));
	return { '--ann-line': `var(--ann-${c})`, '--ann-band': `var(--ann-${c}-band)`, '--ann-weight': `${weight}px`, '--ann-opacity': `${opacity}%` };
}

/** `lookProps` as an inline style. */
export function lookVars(look?: Partial<Look> | null): string {
	return Object.entries(lookProps(look))
		.map(([k, v]) => `${k}: ${v}`)
		.join('; ');
}
