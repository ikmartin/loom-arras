"""Write the trial's frozen-anchor manifest: hashes computed from the frozen files; approval fields marked SIMULATED."""
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1]); state = sys.argv[2]
sha = lambda b: hashlib.sha256(b).hexdigest()
def regions(text):
    bs = text.index("\n", text.index("FROZEN_ANCHOR_PROOF_BEGIN")) + 1
    be = text.rfind("\n", 0, text.index("FROZEN_ANCHOR_PROOF_END")) + 1
    return text[:bs], text[be:]
approval_v2 = {"approved_by": "SIMULATED-FOR-TRIAL (no person approved this)", "approved_at": "2026-11-13", "approval_ref": "SIMULATED: re-approval of sh-0007 v2 (binders moved after the colon; same type up to binder names)", "approval_version": "2"}
approval = {"approved_by": "SIMULATED-FOR-TRIAL (no person approved this)", "approved_at": "2026-11-13",
            "approval_ref": "SIMULATED: lean-trial.md, person's part; stand-in decision by the agent", "approval_version": "1"}
div = (root / "ShowcaseFormal/Frozen/Divergence.lean").read_bytes()
cyc = (root / "ShowcaseFormal/Frozen/CycleLattice.lean").read_bytes()
pre, suf = regions((root / "ShowcaseFormal/Frozen/SaturationV2.lean").read_bytes().decode())
src = "quilt sh-0007@1 (loom version; quilt is not a git repo); file sha256 " 
m = {"schema_version": 1, "manifest_state": "AUTHOR_APPROVED",
     "seal_limits": {"max_body_lines": 3, "max_body_bytes": 240},
     "anchors": [
  {"id": "sh_0003_divergence_v1", "kind": "definition", "author_approval": approval,
   "source": {"revision": "loom sh-0003@1", "range": "drafting/nodes/sh-0003.tex:1-7"},
   "contract": {"id": "showcase.sh-0003", "version": "1"},
   "path": "ShowcaseFormal/Frozen/Divergence.lean", "export": "ShowcaseFormal.divergence",
   "split_policy": {"source_group": "showcase.sh-0003", "mode": "NOT_SPLIT", "ruling_ref": "SIMULATED-no-split"},
   "abi_sha256": "59e0cc3cfd1bb819fb3090a301382a504483cc86abab7f45b2bbe8bcd7e83503",
   "definition_closure": [], "state": "SEALED", "full_file_sha256": sha(div)},
  {"id": "sh_0004_cycle_lattice_v1", "kind": "definition", "author_approval": approval,
   "source": {"revision": "loom sh-0004@1", "range": "drafting/nodes/sh-0004.tex:1-7"},
   "contract": {"id": "showcase.sh-0004", "version": "1"},
   "path": "ShowcaseFormal/Frozen/CycleLattice.lean", "export": "ShowcaseFormal.cycleLattice",
   "split_policy": {"source_group": "showcase.sh-0004", "mode": "NOT_SPLIT", "ruling_ref": "SIMULATED-no-split"},
   "abi_sha256": "a60449beceae225e939d346da767ba6ad565bedf0a9485fcfd213e6ecd84f849",
   "definition_closure": [{"path": "ShowcaseFormal/Frozen/Divergence.lean", "sha256": sha(div)}],
   "state": "SEALED", "full_file_sha256": sha(cyc)},
  {"id": "sh_0007_saturation_v2", "kind": "theorem", "author_approval": approval_v2,
   "source": {"revision": "loom sh-0007@1", "range": "drafting/nodes/sh-0007.tex:1-3"},
   "contract": {"id": "showcase.sh-0007", "version": "2"},
   "path": "ShowcaseFormal/Frozen/SaturationV2.lean", "export": "ShowcaseFormal.cycleLattice_saturated",
   "implementation": {"module": "ShowcaseFormal.Internal.Saturation", "export": "ShowcaseFormal.Internal.cycleLattice_saturated"},
   "split_policy": {"source_group": "showcase.sh-0007", "mode": "NOT_SPLIT", "ruling_ref": "SIMULATED-no-split"},
   "abi_sha256": "3bc3c65ec4baa7267f7aefb3c488c45d3fde273ea25edd546330f441a24ec66f",
   "definition_closure": [{"path": "ShowcaseFormal/Frozen/Divergence.lean", "sha256": sha(div)},
                          {"path": "ShowcaseFormal/Frozen/CycleLattice.lean", "sha256": sha(cyc)}],
   "state": state, "prefix_sha256": sha(pre.encode()), "suffix_sha256": sha(suf.encode()),
   "draft_allowlist": {"frozen_paths": [], "audit_paths": []}}]}
(root / "formal").mkdir(exist_ok=True)
(root / "formal/frozen-anchors.json").write_text(json.dumps(m, indent=2) + "\n")
print("wrote", root / "formal/frozen-anchors.json", "state", state)
