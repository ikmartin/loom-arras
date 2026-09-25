// Every URL arras composes carries the base the bundle was built for, and every corpus URL the data root a host set. Under the suite's own empty base a composed path and a hard-coded one are the same string, so these run under a mocked non-empty base.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { artifactUrl, dataRoot, dataUrl, route, setDataRoot } from './paths';
import { canonUrl, docUrl, keyUrl, masterUrl, nodeUrl, readUrl, tagUrl, taxonUrl, threadUrl, workUrl } from './nav';
import { itemFromPath, pathFor, type Item } from './workspace/item';
import { indexesOf, viewsOf } from './shell/views';
import { fetchSource, sourceUrl } from './source';
import { fetchFragment } from './fragments/fetch';
import { store } from './manifest/client.svelte';
import { capabilities } from './write';
import { document_ } from './pdf/document';
import type { Manifest } from './manifest/types';

vi.mock('$app/paths', () => ({ base: '/sub', assets: '' }));
// PDF.js itself is not the subject: its stand-in hands back the options a document is opened with.
vi.mock('pdfjs-dist', () => ({ GlobalWorkerOptions: {}, getDocument: (options: unknown) => ({ promise: Promise.resolve(options) }) }));

const m = {
	masters: [{ path: 'drafting/main.tex', default: true }],
	canon: [{ path: 'canon/widgets-v1.tex' }],
	nodes: { 'sy-0003': {} },
	keys: { 'sy-0003/proof': { node: 'sy-0003' } },
	publishes: { documents: true, review: true, discussions: true }
} as unknown as Manifest;

afterEach(() => {
	setDataRoot('');
	vi.unstubAllGlobals();
});

describe('a route, under a base', () => {
	it('is prefixed by the base, from every route builder', () => {
		expect({
			route: route('/'),
			nodeUrl: nodeUrl('sy-0003/proof'),
			masterUrl: masterUrl('drafting/main.tex'),
			canonUrl: canonUrl('canon/widgets-v1.tex'),
			docUrl: docUrl(m, 'canon/widgets-v1.tex'),
			readUrl: readUrl('drafting/main.tex', 'sy-0003'),
			keyUrl: keyUrl(m, 'sy-0003/proof'),
			workUrl: workUrl('Kre99'),
			tagUrl: tagUrl('widgets'),
			taxonUrl: taxonUrl('theorem'),
			threadUrl: threadUrl('s-2026-09-16-0001')
		}).toEqual({
			route: '/sub/',
			nodeUrl: '/sub/node/sy-0003/proof',
			masterUrl: '/sub/master/main',
			canonUrl: '/sub/canon/widgets-v1',
			docUrl: '/sub/canon/widgets-v1',
			readUrl: '/sub/master/main#sy-0003',
			keyUrl: '/sub/node/sy-0003#sy-0003-proof',
			workUrl: '/sub/library/Kre99',
			tagUrl: '/sub/tag/widgets',
			taxonUrl: '/sub/taxon/theorem',
			threadUrl: '/sub/session/s-2026-09-16-0001'
		});
	});

	it('names every kind of item under the base, and reads the base back off', () => {
		const items: Item[] = [
			{ kind: 'document', id: 'drafting/main.tex', anchor: 'sy-0003' },
			{ kind: 'document', id: 'canon/widgets-v1.tex' },
			{ kind: 'work', id: 'Kre99', view: 'digest' },
			{ kind: 'node', id: 'sy-0003', note: 'a-2026-09-16-0001' },
			{ kind: 'context', id: 'sy-0003' },
			{ kind: 'session', id: 's-2026-09-16-0001', view: 'did' }
		];
		expect(items.map((i) => pathFor(m, i))).toEqual([
			'/sub/master/main#sy-0003',
			'/sub/canon/widgets-v1',
			'/sub/library/Kre99?view=digest',
			'/sub/node/sy-0003?note=a-2026-09-16-0001',
			'/sub/context/sy-0003',
			'/sub/session/s-2026-09-16-0001?view=did'
		]);
		expect(items.map((i) => itemFromPath(m, pathFor(m, i)))).toEqual(items);
		expect(itemFromPath(m, '/sub/master/main')).toEqual({ kind: 'document', id: 'drafting/main.tex' });
	});

	it('links every view and index of the shell under the base', () => {
		expect(viewsOf(m).map((v) => v.href)).toEqual(['/sub/', '/sub/master/main', '/sub/graph', '/sub/review', '/sub/problems']);
		expect(indexesOf(m).map((x) => x.href)).toEqual(['/sub/threads', '/sub/tags', '/sub/taxa', '/sub/loose']);
	});
});

describe('a corpus URL', () => {
	it('lies under the base\'s build directory by default', () => {
		expect(dataRoot()).toBe('/sub/build/');
		expect(dataUrl('/fragments/sy-0003.html')).toBe('/sub/build/fragments/sy-0003.html');
		expect(sourceUrl('sy-0003/proof')).toBe('/sub/build/source/sy-0003%2Fproof.tex');
		expect(artifactUrl('/refs/Kre99/')).toBe('/sub/refs/Kre99/paper.pdf');
	});

	it('follows a data root a host sets, on another origin, while routes keep the base', () => {
		setDataRoot('https://x.org/corpus/build/');
		expect(dataUrl('manifest.json')).toBe('https://x.org/corpus/build/manifest.json');
		expect(artifactUrl('refs/Kre99')).toBe('https://x.org/corpus/refs/Kre99/paper.pdf');
		expect(route('/graph')).toBe('/sub/graph');
		setDataRoot('');
		expect(dataUrl('manifest.json')).toBe('/sub/build/manifest.json');
	});

	it('is what the manifest poll, a fragment, a key\'s source and the write API probe fetch', async () => {
		const fetched: string[] = [];
		vi.stubGlobal('fetch', async (url: string) => {
			fetched.push(String(url));
			return new Response('', { status: 404 });
		});
		await store.refresh();
		await fetchFragment('fragments/sy-0003.html', 'h').catch(() => undefined);
		await fetchSource('sy-0003');
		await capabilities();
		expect(fetched).toEqual(['/sub/build/manifest.json', '/sub/build/fragments/sy-0003.html', '/sub/build/source/sy-0003.tex', '/sub/_api']);
	});

	it('gives PDF.js its fonts and character maps from under the base', async () => {
		const options = (await document_('/sub/refs/Kre99/paper.pdf')) as unknown as Record<string, unknown>;
		expect(options).toMatchObject({ url: '/sub/refs/Kre99/paper.pdf', standardFontDataUrl: '/sub/pdfjs/standard_fonts/', cMapUrl: '/sub/pdfjs/cmaps/' });
	});
});
