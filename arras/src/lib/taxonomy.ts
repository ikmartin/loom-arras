// One palette for taxa, shared by the document and the graph (running-requests: "should match the color of the taxons, and there should be one place to set these colors").
//
// The colours are tokens in `theme.css` and nothing here knows a hex value; what this decides is only which token a taxon gets. Assignment is by the manifest's own `style` first -- a remark reads quietly whatever it is called -- and then by the taxon's position among the rest, so every taxon gets a colour and two taxa never share one until the palette runs out.
//
// Keyed by style and position rather than by name on purpose: `Theorem`, `Lemma` and `Definition` are one publisher's vocabulary, and a corpus whose taxa are `Widget` and `Gadget` deserves the same colouring as one whose taxa are Bourbaki's.

import type { Manifest } from '$lib/manifest/types';

/** How many distinct hues the palette offers before it repeats. Defined in `theme.css` as `--taxon-1` … `--taxon-N`. */
export const PALETTE = 8;

/** The CSS custom property holding a taxon's colour, as a `var(...)` reference. */
export function taxonTone(m: Manifest | null, taxon: string | undefined | null): string {
	if (!m || !taxon) return 'var(--rule-strong)';
	const entry = m.taxa?.[taxon];
	if (entry?.style === 'remark') return 'var(--taxon-remark)';
	// Sorted, so a taxon keeps its colour as the corpus grows: adding a node must not repaint the graph.
	const ordered = Object.keys(m.taxa ?? {})
		.filter((name) => m.taxa[name]?.style !== 'remark')
		.sort();
	const at = ordered.indexOf(taxon);
	if (at < 0) return 'var(--rule-strong)';
	return `var(--taxon-${(at % PALETTE) + 1})`;
}

/** Every taxon with the tone it was given, for a legend. */
export function taxonLegend(m: Manifest | null): { taxon: string; tone: string; count: number }[] {
	if (!m) return [];
	return Object.entries(m.taxa ?? {})
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([taxon, t]) => ({ taxon, tone: taxonTone(m, taxon), count: t.count ?? 0 }));
}
