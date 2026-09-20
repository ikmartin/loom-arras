// One palette for taxa, shared by the document and the graph (running-requests: "should match the color of the taxons, and there should be one place to set these colors").
//
// **Three colours, by style.** A result, a definition, an aside — which is the grouping loom already publishes in `taxa[name].style`, and the only one a viewer can make without knowing what the words mean. Eight hues, one per taxon, left a finding with nothing of its own to wear: the annotation colour sat in the same register as the taxa and the page had no spare register left (DR-175). Three leaves one.
//
// Keyed by style rather than by name on purpose: `Theorem`, `Lemma` and `Definition` are one publisher's vocabulary, and a corpus whose taxa are `Widget` and `Gadget` is coloured the same way. It is stable for the same reason — nothing here depends on how many taxa there are or on what order they arrived in, so adding a node never repaints the graph.

import type { Manifest } from '$lib/manifest/types';

/** The CSS custom property holding a taxon's colour, as a `var(...)` reference. */
export function taxonTone(m: Manifest | null, taxon: string | undefined | null): string {
	if (!m || !taxon) return 'var(--rule-strong)';
	const style = m.taxa?.[taxon]?.style;
	if (style === undefined) return 'var(--rule-strong)';
	if (style === 'remark') return 'var(--taxon-aside)';
	// Anything a publisher styles as neither a remark nor a definition is a claim: unknown styles read as results
	// rather than as nothing, because a viewer that meets a style it has not heard of should still draw the node.
	return style === 'definition' ? 'var(--taxon-definition)' : 'var(--taxon-result)';
}

/** Every taxon with the tone it was given, for a legend. */
export function taxonLegend(m: Manifest | null): { taxon: string; tone: string; count: number }[] {
	if (!m) return [];
	return Object.entries(m.taxa ?? {})
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([taxon, t]) => ({ taxon, tone: taxonTone(m, taxon), count: t.count ?? 0 }));
}
