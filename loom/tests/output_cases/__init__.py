"""The output check's case table (plan 0.18.3): every leaf command, how it prints, and the cases it is run in.

One module per group of commands, merged here. `KIND` says how a command prints: `report` (through `loom.cli.report`, held to every rule of `tests/unit/test_output.py`), `raw` (the author's own text, a patch, a page, a link: its body is not a report, though its refusals and its `--json` are), or `running` (it runs until stopped, and is not run). `CASES` lists, per command, the runs to make: normal ones and refusals, each with the exit code book 12.1 gives it. 0.18.4's checks of K3 read the same table.
"""

from __future__ import annotations

from tests.output_cases import agents, core, history, refs
from tests.output_cases.base import Case, Setup

KIND: dict[str, str] = {**core.KIND, **refs.KIND, **history.KIND, **agents.KIND}
CASES: dict[str, list[Case]] = {**core.CASES, **refs.CASES, **history.CASES, **agents.CASES}

__all__ = ["CASES", "KIND", "Case", "Setup"]
