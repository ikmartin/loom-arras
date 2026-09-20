# arras

A static viewer for node-based text corpora. arras reads a build directory conforming to the loom–arras interface (`docs/specs/` in the [loom-arras workspace](https://github.com/ikmartin/loom-arras)): a `manifest.json` carrying the graph and every non-textual fact, and HTML fragments in a fixed semantic dialect. It renders node pages, a document view per master, a review panel, a problems page, a dependency graph, threads, indexes, and search, and it re-renders whenever the manifest changes. It knows nothing about LaTeX, about [loom](https://github.com/ikmartin/loom), or about mathematics; loom is its first publisher.

Status: pre-alpha, under construction milestone by milestone.

## For users

You do not need this repository or Node. The built viewer ships inside loom; `loom serve` serves it. Any static file server can serve a build directory plus the bundle as well.

## For developers

Requires Node 20 or newer.

```
git clone https://github.com/ikmartin/arras
cd arras
npm ci
npm run check          # svelte-check
npm run test:unit -- --run
npm run build          # SPA build into build/
npx playwright install chromium   # once, for the end-to-end tests
npm run test:e2e
```

`npm run build:pip` copies `build/` into the optional pip wrapper under `python/`. loom vendors the same `build/` with its own `scripts/vendor_arras.py`.

## License

AGPL-3.0-or-later; see `LICENSE` and `NOTICE`.
