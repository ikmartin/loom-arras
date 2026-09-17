// Where the reader is in the document, for the contents rail's position bar.
//
// The bar used to be driven by `location.hash`, which meant it appeared only after someone clicked a contents entry and then never moved again. Two faults followed from that: a reader who scrolled had no idea where they were, and an entry whose key is not already slug-shaped -- an unlabelled section, keyed `drafts/main.tex#section:3` -- never matched the hash at all, so its bar never lit even when clicked.
//
// So the position is tracked from the scroll instead, and the comparison is made on the published element id both sides agree on.

import { anchorId } from "$lib/nav";

/** The reading line: a heading counts as the one you are in once it has passed this far up the viewport. */
const LINE = 96;

class Reading {
  /** The published element id of the section on screen, or '' when no document is being read. */
  section = $state("");
}

export const reading = new Reading();

/**
 * Follow the reader's position through a document, setting `reading.section` as they scroll.
 *
 * Parameters
 * ----------
 * ids : string[]
 *     The published element ids of the contents entries, in document order. Only these are considered, so a heading too deep to appear in the contents never steals the bar and leaves it pointing at nothing.
 *
 * Returns
 * -------
 * () => void
 *     Cleanup; also clears the section, so leaving the read view returns the rail to the hash.
 */
export function followReading(ids: string[]): () => void {
  if (typeof window === "undefined" || !ids.length) return () => {};
  let frame = 0;

  const pick = () => {
    frame = 0;
    // the last heading at or above the reading line; the first entry stands until one reaches it, so the bar
    // is showing before a reader has scrolled at all
    let found = ids[0];
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el && el.getBoundingClientRect().top <= LINE) found = id;
    }
    reading.section = found;
  };

  const onScroll = () => {
    if (!frame) frame = requestAnimationFrame(pick);
  };

  pick();
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });
  return () => {
    if (frame) cancelAnimationFrame(frame);
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
    reading.section = "";
  };
}

/** The published ids of contents entries, in document order. */
export function sectionIds(entries: { key: string }[]): string[] {
  return entries.map((e) => anchorId(e.key));
}
