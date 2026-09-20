# arras (pip wrapper)

Vendors the built arras viewer so a Python tool can serve it without Node. `arras.bundle_path()` returns the directory holding `index.html`. Build the bundle first with `npm run build && npm run build:pip` in the repository root; publishing to PyPI is the maintainer's decision.
