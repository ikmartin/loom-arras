cd ~/dev/loom-arras/arras && npm run build &&
  (cd ../loom && uv run python scripts/vendor_arras.py ../arras/build)
