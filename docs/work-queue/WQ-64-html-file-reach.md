# WQ-64 · What an HTML file in a quilt can reach

**Repo:** loom, arras

## Trigger

An HTML file the author keeps opening has to export loom's records to a shown file by hand, or loses state they wanted kept; or a second quilt builds a list of open boxes.

## Why deferred

No HTML file in real use has needed loom's records or lasting state yet, and only one quilt has wanted a list of open boxes. What such a list should show is unsettled: quant's 518 boxes hold the same material at up to three levels, and they mix self-assessments with tasks.

## Rough design

- **Loom's records:** a read-only feed on the frames origin. An agent's page could then show "verified" inside the viewer where it reads as loom's own claim (P15), and it could repeat Review and the graph (V2), so it should carry only what a named page needs.
- **Lasting state:** a store under `.loom/` that each HTML file owns and that cannot touch the person's files. A stable port per quilt is the cheap half, but it leaves the state in one browser where no agent can read it.
- **A list in loom:** a derived index of the open boxes in the manifest (P2, P3), each row opening the line where it lives (V7). The first HTML files people keep using should decide its shape.
