"""Generate docs/mcp-tools.json, the tools `loom mcp` offers, from the click command tree: each tool's name, the command it runs, its description, its input schema and its hints. Checked in so a changed flag shows as a diff.

Usage: uv run python scripts/gen_mcp_tools.py [--check]   (--check exits 1 when the checked-in file is stale)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loom.mcp.tools import hints, schema, tools

OUT = Path(__file__).resolve().parent.parent / "docs" / "mcp-tools.json"


def generate() -> str:
    surface = [
        {
            "name": s.name,
            "command": f"loom {s.path}",
            "description": s.description,
            "inputSchema": schema(s),
            "annotations": hints(s),
        }
        for s in tools()
    ]
    return json.dumps(surface, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


if __name__ == "__main__":
    text = generate()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.read_text(encoding="utf-8") == text else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
