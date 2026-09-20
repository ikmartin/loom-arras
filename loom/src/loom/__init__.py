"""loom: a tool for atomized mathematical development.

A quilt is a LaTeX paper whose theorem-like environments and sections carry permanent ids as labels. loom reads the dependency graph from the references the author already writes, keeps a ledger of accepted statements with content hashes, anchors review comments to quoted text, and publishes a build directory for the arras viewer. See the design book in the loom-arras workspace.
"""

from loom.version import INTERFACE_VERSION, __version__

__all__ = ["INTERFACE_VERSION", "__version__"]
