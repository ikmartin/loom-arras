# The hostile quilt

A quilt built to break loom and arras rather than to be read. Six attack directions, each in its own file or section, each chosen because it exercises a boundary the code actually has rather than one it might have.

Nothing here is a supported input. The point is what the tools do when the input is not supported: **refuse clearly, degrade visibly, or fail in a way nobody can debug.** Only the third is a bug, and the report in `docs/reports/hostile-demo.md` says which is which.

It is not a test fixture and no suite depends on it. Rebuild what it produces with `loom build --quilt demos/hostile` and read the report beside it.
