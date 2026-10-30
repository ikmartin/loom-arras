// A page the quilt holds is served in the viewer's own origin, and an agent writes `build/**`. Such a page must not run as the viewer: one that did could read the token from `/_api` and post the author's acts naming no author, which the publisher takes for the author's own click (K5).
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { expect, test } from '../served';

/** Synchronous requests, so that by the page's `load` whatever the script did has already reached the publisher. */
const PAYLOAD = `
var x = new XMLHttpRequest();
x.open('GET', '/_api', false);
x.send();
var token = JSON.parse(x.responseText).token;
x.open('POST', '/_api/session-new', false);
x.setRequestHeader('Content-Type', 'application/json');
x.setRequestHeader('X-Loom-Token', token);
x.send(JSON.stringify({ title: 'planted' }));
`;

const PLANTED: Record<string, string> = {
	'build/agent/x.html': `<!doctype html><title>planted</title><script>${PAYLOAD}</script>`,
	'digests/storage/arxiv/2101.00001v1/src/figure.svg': `<svg xmlns="http://www.w3.org/2000/svg"><script><![CDATA[${PAYLOAD}]]></script></svg>`
};

for (const [path, text] of Object.entries(PLANTED)) {
	test(`${path.split('.').pop()} under ${path.split('/')[0]}/ runs no script as the viewer, so it writes nothing`, async ({ page, served }) => {
		const file = join(served.root, path);
		mkdirSync(dirname(file), { recursive: true });
		writeFileSync(file, text);
		const asked: string[] = [];
		page.on('request', (r) => {
			if (new URL(r.url()).pathname.startsWith('/_api')) asked.push(r.url());
		});
		const res = await page.goto(`/${path}`);
		expect(res?.status()).toBe(200);
		const index = join(served.root, '.loom/sessions/index.jsonl');
		expect(existsSync(index) ? readFileSync(index, 'utf8') : '', 'the session index').not.toContain('planted');
		expect(asked, 'requests the planted page made to the write API').toEqual([]);
		expect(res?.headers()['content-security-policy']).toBe('sandbox');
	});
}
