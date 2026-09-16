// Which external nodes this corpus actually leans on.
//
// A digest holds every theorem-like result of a cited paper, so digesting one paper wholesale brings in a hundred external nodes of which two or three carry weight. Reachedness is the difference: an external node is reached when something the corpus itself wrote depends on it, transitively. It decides three things that would otherwise be unusable at that scale -- which external nodes belong in the review queue, which appear in the graph by default, and which of a digest's results are folded away when reading it.
//
// Note that depth is the wrong test and reachedness is the right one: a cited paper's result you lean on needs checking whoever cited it, and one you never use needs nothing.

import type { Manifest } from "$lib/manifest/types";

/**
 * The keys of every external node something in the corpus depends on.
 *
 * Built from `keys[k].closure`, the transitive closure the publisher already writes, so this needs nothing new from loom. The closure of a reached external node is included too: a statement whose standing assumptions are off-screen is not shown.
 */
export function reachedExternal(m: Manifest): Set<string> {
  const external = new Set(
    Object.values(m.nodes)
      .filter((n) => n.external)
      .map((n) => n.id),
  );
  const out = new Set<string>();
  for (const key of Object.values(m.keys)) {
    const node = m.nodes[key.node];
    if (!node || node.external) continue; // only what the corpus itself wrote reaches
    for (const dep of key.closure) {
      if (!external.has(dep)) continue;
      out.add(dep);
      for (const inner of m.keys[dep]?.closure ?? [])
        if (external.has(inner)) out.add(inner);
    }
  }
  return out;
}

/** Whether a node should be shown by default: everything the corpus wrote, plus the external nodes it reaches. */
export function isShownByDefault(
  m: Manifest,
  id: string,
  reached: Set<string>,
): boolean {
  const node = m.nodes[id];
  if (!node) return false;
  return !node.external || reached.has(id);
}
