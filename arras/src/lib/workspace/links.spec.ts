import { describe, expect, it } from 'vitest';
import type { Manifest } from '$lib/manifest/types';
import { holding, itemForQuilt } from './links';
import { workspace } from './store.svelte';
import { linkName } from './names';

// The least of a manifest that a `quilt:` link reads: two documents, a node with a proof and an equation, a cited work, an annotation on each kind of target, and a session.
const m = {
	masters: [{ path: 'drafting/main.tex', default: true }],
	canon: [],
	nodes: {
		'sy-0003': { kind: 'environment', taxon: 'Theorem', numbers: { 'drafting/main.tex': { number: '2.1' } }, reached_by: ['drafting/main.tex'] },
		'sy-0003/proof': { kind: 'proof', taxon: 'proof', numbers: {}, reached_by: ['drafting/main.tex'] }
	},
	keys: { 'sy-0003': { node: 'sy-0003' }, 'sy-0003/proof': { node: 'sy-0003' } },
	regions: { 'sy-0003#eq:fix': { container: 'sy-0003', label: 'eq:fix', numbers: { 'drafting/main.tex': { number: '4' } } } },
	references: { Kre99: { citekey: 'Kre99', work: 'arXiv:math/9810166v2', works: ['arXiv:math/9810166v2'] } },
	annotations: {
		'a-2026-09-16-0001': { id: 'a-2026-09-16-0001', kind: 'objection', target: { key: 'sy-0003' } },
		'a-2026-09-16-0004': { id: 'a-2026-09-16-0004', kind: 'note', target: { key: 'drafting/main.tex' } },
		'a-2026-09-17-0003': { id: 'a-2026-09-17-0003', kind: 'question', target: { key: 'arXiv:math/9810166v2', page: 2 } },
		'a-2026-09-23-0002': { id: 'a-2026-09-23-0002', kind: 'objection', target: { key: 'sy-0003#eq:fix' } },
		'a-2026-09-23-0004': { id: 'a-2026-09-23-0004', kind: 'question', target: { key: 'sy-0003#eq:fix' }, in_reply_to: 'a-2026-09-23-0002' }
	},
	sessions: [{ id: 's-2026-09-16-0001', title: 'referee' }],
	threads: {}
} as unknown as Manifest;

describe('a quilt: link', () => {
	it('names each kind of thing the quilt owns', () => {
		expect(itemForQuilt(m, 'sy-0003')).toMatchObject({ kind: 'node', id: 'sy-0003' });
		expect(itemForQuilt(m, 'drafting/main.tex#sy-0003')).toEqual({ kind: 'document', id: 'drafting/main.tex', anchor: 'sy-0003' });
		expect(itemForQuilt(m, 's-2026-09-16-0001')).toEqual({ kind: 'session', id: 's-2026-09-16-0001' });
		expect(itemForQuilt(m, 'sy-9999')).toMatchObject({ kind: 'node', id: 'sy-9999' }); // an unknown key still has a page, which says so
	});
	it('opens an annotation at its target, with its box', () => {
		expect(itemForQuilt(m, 'a-2026-09-16-0001')).toMatchObject({ kind: 'node', id: 'sy-0003', note: 'a-2026-09-16-0001' });
		expect(itemForQuilt(m, 'a-2026-09-16-0004')).toEqual({ kind: 'document', id: 'drafting/main.tex', note: 'a-2026-09-16-0004' });
		expect(itemForQuilt(m, 'a-2026-09-17-0003')).toEqual({ kind: 'work', id: 'Kre99', place: { page: 2, annot: 'a-2026-09-17-0003' } });
		// a box drawn round an equation is filed under the region's key; it opens the node it is in (the 0.14 study opened `/node/sy-0003#eq:fix`, a node that does not exist)
		expect(itemForQuilt(m, 'a-2026-09-23-0002')).toMatchObject({ kind: 'node', id: 'sy-0003', note: 'a-2026-09-23-0002' });
		// a reply opens the box of the thread it is in, which is where it is read (the 0.14 study: a link to one opened nothing)
		expect(itemForQuilt(m, 'a-2026-09-23-0004')).toMatchObject({ kind: 'node', id: 'sy-0003', note: 'a-2026-09-23-0002' });
	});
	it('goes to a place in a node: an equation of it, or its proof', () => {
		expect(itemForQuilt(m, 'sy-0003#eq:fix')?.anchor).toBe('sy-0003-eq-fix');
		expect(itemForQuilt(m, 'sy-0003#sy-0003/proof')?.anchor).toBeTruthy();
	});
});

describe('an empty link', () => {
	it('is named as a reader names the thing', () => {
		expect(linkName(m, 'quilt:sy-0003')).toBe('Theorem 2.1');
		expect(linkName(m, 'quilt:sy-0003#eq:fix')).toBe('(4) in Theorem 2.1');
		expect(linkName(m, 'quilt:drafting/main.tex')).toBe('main.tex');
		expect(linkName(m, 'quilt:drafting/main.tex#sy-0003')).toBe('Theorem 2.1');
		expect(linkName(m, 'quilt:a-2026-09-16-0001')).toBe('objection on Theorem 2.1');
		expect(linkName(m, 'quilt:a-2026-09-23-0004')).toBe('reply on (4) in Theorem 2.1'); // not `question on`, which reads as a new one
		expect(linkName(m, 'quilt:s-2026-09-16-0001')).toBe('referee');
		expect(linkName(m, 'cited:arxiv:math/9810166v2?page=3')).toBe('Kre99 p. 3');
		expect(linkName(m, 'quilt:sy-9999')).toBe('sy-9999');
	});
});

describe('a node link where a document holding the node is open (DR-280-ikmartin)', () => {
	const held = { ...m, nodes: { ...m.nodes, 'sy-0003': { ...m.nodes['sy-0003'], reached_by: ['drafting/main.tex', 'drafting/talk.tex'] } } } as unknown as Manifest;
	const doc = (id: string) => ({ kind: 'document' as const, id });
	const session = { kind: 'session' as const, id: 's-2026-09-16-0001' };
	const node = { kind: 'node' as const, id: 'sy-0003', anchor: 'sy-0003-eq-fix' };

	it('is revealed in the document on screen, at its place, with its note', () => {
		workspace.reset();
		workspace.openIn(doc('drafting/main.tex'), 0);
		workspace.beside(session, 0);
		expect(holding(held, node, 1)).toEqual({ item: { kind: 'document', id: 'drafting/main.tex', anchor: 'sy-0003-eq-fix' }, pane: 0 });
		expect(holding(held, { kind: 'node', id: 'sy-0003', note: 'a-1' }, 1)?.item).toEqual({ kind: 'document', id: 'drafting/main.tex', anchor: 'sy-0003', note: 'a-1' });
	});

	it('prefers the document the link stands in, then one on screen, then the tab last looked at', () => {
		workspace.reset();
		workspace.openIn(doc('drafting/main.tex'), 0);
		workspace.beside(doc('drafting/talk.tex'), 0);
		expect(holding(held, node, 1)?.item.id).toBe('drafting/talk.tex'); // the link's own document
		expect(holding(held, node, 0)?.item.id).toBe('drafting/main.tex');
		// both behind other tabs: the one looked at last
		workspace.openIn(session, 1);
		workspace.openIn({ kind: 'node', id: 'sy-9999' }, 0);
		workspace.activate(1, 'document:drafting/talk.tex');
		workspace.activate(1, 'session:s-2026-09-16-0001');
		expect(holding(held, node, -1)?.item.id).toBe('drafting/talk.tex');
	});

	it('is nothing for a document that does not hold it, or for anything but a node', () => {
		workspace.reset();
		workspace.openIn(doc('drafting/other.tex'), 0);
		expect(holding(held, node, 1)).toBeNull();
		workspace.openIn(doc('drafting/main.tex'), 0);
		expect(holding(held, doc('drafting/talk.tex'), 1)).toBeNull();
	});
});
