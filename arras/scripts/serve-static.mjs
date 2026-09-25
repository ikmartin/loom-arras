// Serve a staged copy of the app (scripts/bundle.mjs) the way `loom serve` does, for the Playwright configs that have no publisher behind them.
//
// Usage: node scripts/serve-static.mjs DIR PORT
//
// Resolution follows loom's `render/serve.py`: `/build/...` is a file of the corpus or 404, taken literally since fragment names carry `%2F`; `/digests/storage/...` is percent-decoded; a missing `_app/` file or asset is 404, never the shell; `/_api` is 404, so the viewer shows no editing affordances; every other path is the app shell, dots in keys included. Listens on 127.0.0.1 only.

import { createServer } from 'node:http';
import { createReadStream, statSync } from 'node:fs';
import { extname, join, resolve, sep } from 'node:path';

const [dirArg, portArg] = process.argv.slice(2);
if (!dirArg || !portArg) {
	console.error('usage: node scripts/serve-static.mjs DIR PORT');
	process.exit(2);
}
const root = resolve(dirArg);
const shell = join(root, 'index.html');
if (!isFile(shell)) {
	console.error(`${root} has no index.html; stage it with scripts/bundle.mjs`);
	process.exit(2);
}

const TYPES = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8',
	'.mjs': 'text/javascript; charset=utf-8',
	'.css': 'text/css; charset=utf-8',
	'.json': 'application/json; charset=utf-8',
	'.map': 'application/json; charset=utf-8',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.jpeg': 'image/jpeg',
	'.gif': 'image/gif',
	'.ico': 'image/x-icon',
	'.woff': 'font/woff',
	'.woff2': 'font/woff2',
	'.ttf': 'font/ttf',
	'.pfb': 'application/octet-stream',
	'.bcmap': 'application/octet-stream',
	'.txt': 'text/plain; charset=utf-8',
	'.tex': 'text/plain; charset=utf-8',
	'.xml': 'application/xml',
	'.pdf': 'application/pdf',
	'.webmanifest': 'application/manifest+json',
	'.wasm': 'application/wasm'
};
// loom's ASSET_SUFFIXES: a missing file with one of these is a 404 rather than a route of the app
const ASSETS = new Set(['.js', '.mjs', '.css', '.map', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.json', '.woff', '.woff2', '.ttf', '.txt', '.webmanifest']);

function isFile(p) {
	try {
		return statSync(p).isFile();
	} catch {
		return false;
	}
}

/** A file under `base`, or null when `rel` escapes it or names nothing. */
function within(base, rel) {
	const target = resolve(base, rel);
	return (target === base || target.startsWith(base + sep)) && isFile(target) ? target : null;
}

function locate(path) {
	if (path === '/_api' || path.startsWith('/_api/')) return null;
	if (path.startsWith('/build/')) return within(join(root, 'build'), path.slice('/build/'.length));
	if (path.startsWith('/digests/storage/')) {
		let rel;
		try {
			rel = decodeURIComponent(path.slice('/digests/storage/'.length));
		} catch {
			return null;
		}
		return within(join(root, 'digests', 'storage'), rel);
	}
	const rel = path.replace(/^\/+/, '');
	if (!rel) return shell;
	const found = within(root, rel) ?? within(root, join(rel, 'index.html'));
	if (found) return found;
	if (rel.startsWith('_app/') || ASSETS.has(extname(rel).toLowerCase())) return null;
	return shell;
}

const server = createServer((req, res) => {
	if (req.method !== 'GET' && req.method !== 'HEAD') {
		res.writeHead(405, { Allow: 'GET, HEAD' }).end();
		return;
	}
	const path = (req.url ?? '/').split('?', 1)[0].split('#', 1)[0];
	const file = locate(path);
	if (!file) {
		res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('not found');
		return;
	}
	const st = statSync(file);
	const etag = `"${st.size.toString(16)}-${Math.floor(st.mtimeMs).toString(16)}"`;
	const headers = { ETag: etag, 'Cache-Control': 'no-cache', 'Content-Type': TYPES[extname(file).toLowerCase()] ?? 'application/octet-stream' };
	if (req.headers['if-none-match'] === etag) {
		res.writeHead(304, headers).end();
		return;
	}
	res.writeHead(200, { ...headers, 'Content-Length': st.size });
	if (req.method === 'HEAD') res.end();
	else createReadStream(file).pipe(res);
});
server.listen(Number(portArg), '127.0.0.1', () => console.log(`serving ${root} on http://127.0.0.1:${portArg}`));
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => process.exit(0));
