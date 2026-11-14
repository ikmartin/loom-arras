import sys, json
from pathlib import Path
from loom.cli._quilt import open_scan
from loom.refs.add import identify
from loom.refs.ingest import identify_document
root = Path(sys.argv[1]); pdf = Path(sys.argv[2]); drop = set(sys.argv[3:])
bib = {k: v for k, v in open_scan(str(root)).bib.items() if k not in drop}
seen = identify(root, bib, pdf, online=False)
print(json.dumps(seen.to_json(), indent=1))
