import { describe, expect, it } from "vitest";
import { reachedExternal } from "./reached";
import type { Manifest } from "./manifest/types";

/** A corpus with one own lemma that uses one external result, plus `spare` external results nothing touches. */
function corpus(spare: number): Manifest {
  const nodes: Record<string, unknown> = {
    "rl-0001": { id: "rl-0001", external: false },
    "Man12-prop-3.2": { id: "Man12-prop-3.2", external: true },
    "Man12-setup": { id: "Man12-setup", external: true },
  };
  const keys: Record<string, unknown> = {
    "rl-0001": { node: "rl-0001", closure: ["Man12-prop-3.2"] },
    // the standing assumptions the reached result rests on: off-screen hypotheses are not a useful way to read it
    "Man12-prop-3.2": { node: "Man12-prop-3.2", closure: ["Man12-setup"] },
    "Man12-setup": { node: "Man12-setup", closure: [] },
  };
  for (let i = 0; i < spare; i++) {
    const id = `Man12-rem-${i}`;
    nodes[id] = { id, external: true };
    keys[id] = { node: id, closure: [] };
  }
  return { nodes, keys } as unknown as Manifest;
}

describe("reachedExternal", () => {
  it("is what the corpus depends on, plus what that rests on", () => {
    expect([...reachedExternal(corpus(0))].sort()).toEqual([
      "Man12-prop-3.2",
      "Man12-setup",
    ]);
  });

  it("is stable when a digest brings in results nothing uses", () => {
    // digesting a paper wholesale adds ninety-odd external nodes; the review queue and the graph must not move
    const before = [...reachedExternal(corpus(0))].sort();
    expect([...reachedExternal(corpus(93))].sort()).toEqual(before);
  });

  it("does not count one external node reaching another as reached", () => {
    // only what this corpus wrote reaches: a digest's internal edges are the cited paper's business
    const m = corpus(0);
    delete (m.keys as Record<string, unknown>)["rl-0001"];
    delete (m.nodes as Record<string, unknown>)["rl-0001"];
    expect([...reachedExternal(m)]).toEqual([]);
  });
});
