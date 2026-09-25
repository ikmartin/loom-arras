// Where the reader is in the document, for the contents rail's position bar.
//
// The bar used to be driven by `location.hash`, which meant it appeared only after someone clicked a contents entry and then never moved again. Two faults followed from that: a reader who scrolled had no idea where they were, and an entry whose key is not already slug-shaped -- an unlabelled section, keyed `drafts/main.tex#section:3` -- never matched the hash at all, so its bar never lit even when clicked.
//
// So the position is tracked from the scroll instead, and the comparison is made on the published element id both sides agree on.

import { anchorId } from "$lib/nav";

/** The reading line: a heading counts as the one you are in once it has passed this far below the top of what scrolls. */
const LINE = 32;

/** The top of the reader's view: the pane's scrolling body when there is one, else the window. */
function topOf(scroller: HTMLElement | null): number {
  return scroller ? scroller.getBoundingClientRect().top : 0;
}

class Reading {
  /** The published element id of the section on screen, or '' when no document is being read. */
  section = $state("");
  /** The key of the result being read: the last statement or proof whose start has passed the reading line. '' when no document is being read. */
  node = $state("");
}

export const reading = new Reading();

/**
 * Follow the reader's position through a document, setting `reading.section` as they scroll.
 *
 * Parameters
 * ----------
 * root : HTMLElement
 *     The mounted document; ids are looked up inside it, since two open documents repeat them.
 * ids : string[]
 *     The published element ids of the contents entries, in document order. Only these are considered, so a heading too deep to appear in the contents never steals the bar and leaves it pointing at nothing.
 * scroller : HTMLElement | null
 *     What scrolls: the pane's body. A document in a pane never scrolls the window.
 *
 * Returns
 * -------
 * () => void
 *     Cleanup; also clears the section, so leaving the read view returns the rail to the hash.
 */
export function followReading(root: HTMLElement, ids: string[], scroller: HTMLElement | null): () => void {
  if (typeof window === "undefined" || !ids.length) return () => {};
  let frame = 0;

  const pick = () => {
    frame = 0;
    // the last heading at or above the reading line; the first entry stands until one reaches it, so the bar
    // is showing before a reader has scrolled at all
    let found = ids[0];
    const line = topOf(scroller) + LINE;
    for (const id of ids) {
      const el = root.querySelector(`[id="${CSS.escape(id)}"]`);
      if (el && el.getBoundingClientRect().top <= line) found = id;
    }
    reading.section = found;
  };

  const onScroll = () => {
    if (!frame) frame = requestAnimationFrame(pick);
  };

  pick();
  const on = scroller ?? window;
  on.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  return () => {
    if (frame) cancelAnimationFrame(frame);
    on.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
    reading.section = "";
  };
}

/** The published ids of contents entries, in document order. */
export function sectionIds(entries: { key: string }[]): string[] {
  return entries.map((e) => anchorId(e.key));
}

/** How far down the window a result counts as being read: a third of the way, where the eye rests, rather than the heading line the contents bar uses. */
const NODE_LINE = 0.35;

/**
 * Follow which result the reader is on, setting `reading.node` as they scroll.
 *
 * The last statement or proof whose top has passed the reading line wins, so prose between two results keeps the one above rather than falling back to the section, and the local graph that follows this does not flicker between a result and its section on every paragraph. Before any result is reached, the first result stands.
 *
 * Parameters
 * ----------
 * root : HTMLElement
 *     The mounted document. Its results are re-read on each frame, so expanding an inclusion or a proof needs no notice.
 * scroller : HTMLElement | null
 *     What scrolls: the pane's body.
 *
 * Returns
 * -------
 * () => void
 *     Cleanup; also clears the node.
 */
export function followNodes(root: HTMLElement, scroller: HTMLElement | null): () => void {
  if (typeof window === "undefined") return () => {};
  let frame = 0;
  const pick = () => {
    frame = 0;
    const line = scroller ? topOf(scroller) + scroller.clientHeight * NODE_LINE : window.innerHeight * NODE_LINE;
    const results = root.querySelectorAll<HTMLElement>("div.env[data-key], details.env-proof[data-key]");
    // tops increase in document order, so the last one above the line is found by bisection rather than by measuring every result on every frame
    let lo = 0;
    let hi = results.length - 1;
    let found = -1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (results[mid].getBoundingClientRect().top <= line) {
        found = mid;
        lo = mid + 1;
      } else hi = mid - 1;
    }
    // before the first result is reached, the one about to be read stands in, or the first section when the document has no results
    const first = root.querySelector<HTMLElement>("section[data-key], section[data-id]");
    const key = found >= 0 ? (results[found].dataset.key ?? "") : results.length ? (results[0].dataset.key ?? "") : (first?.dataset.key ?? first?.dataset.id ?? "");
    if (key !== reading.node) reading.node = key;
  };
  const onScroll = () => {
    if (!frame) frame = requestAnimationFrame(pick);
  };
  pick();
  const on = scroller ?? window;
  on.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  return () => {
    if (frame) cancelAnimationFrame(frame);
    on.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
    reading.node = "";
  };
}
