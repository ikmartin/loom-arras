import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import type { Manifest } from '$lib/manifest/types';
import { pdf } from '$lib/pdf.svelte';
import { sessionView } from '$lib/sessions/sessions.svelte';
import { follow, holding, interceptLinks, itemForQuilt, openChat, soleSession } from './links';
import { itemKey, type Item } from './item';
import { workspace } from './store.svelte';
import { linkName } from './names';

vi.mock('$app/navigation', () => ({ goto: vi.fn(async () => {}) }));

// The least of a manifest that a `quilt:` link reads: two documents, a node with a proof and an equation, a cited work, an annotation on each kind of target, and a session.
const m = {
	masters: [{ path: 'drafting/main.tex', default: true }],
	canon: [{ path: 'canon/main-v1.tex' }],
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
		expect(itemForQuilt(m, 'canon/main-v1.tex')).toEqual({ kind: 'document', id: 'canon/main-v1.tex' }); // a landmark, not an unknown node
		expect(itemForQuilt(m, 'sy-9999')).toMatchObject({ kind: 'node', id: 'sy-9999' }); // an unknown key still has a page, which says so
	});
	it('opens an annotation at its target, with its box', () => {
		expect(itemForQuilt(m, 'a-2026-09-16-0001')).toMatchObject({ kind: 'node', id: 'sy-0003', note: 'a-2026-09-16-0001' });
		expect(itemForQuilt(m, 'a-2026-09-16-0004')).toEqual({ kind: 'document', id: 'drafting/main.tex', note: 'a-2026-09-16-0004' });
		expect(itemForQuilt(m, 'a-2026-09-17-0003')).toEqual({ kind: 'work', id: 'Kre99', place: { page: 2, annot: 'a-2026-09-17-0003' } });
		// a box drawn round an equation is filed under the region's key; it opens the node it is in, never `/node/sy-0003#eq:fix`, a node that does not exist
		expect(itemForQuilt(m, 'a-2026-09-23-0002')).toMatchObject({ kind: 'node', id: 'sy-0003', note: 'a-2026-09-23-0002' });
		// a reply opens the box of the thread it is in, which is where it is read
		expect(itemForQuilt(m, 'a-2026-09-23-0004')).toMatchObject({ kind: 'node', id: 'sy-0003', note: 'a-2026-09-23-0002' });
	});
	it('goes to a place in a node: an equation of it, or its proof', () => {
		expect(itemForQuilt(m, 'sy-0003#eq:fix')?.anchor).toBe('sy-0003-eq-fix');
		expect(itemForQuilt(m, 'sy-0003#sy-0003/proof')?.anchor).toBe('sy-0003-proof');
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

const doc = (id: string): Item => ({ kind: 'document', id });
const node = (id: string): Item => ({ kind: 'node', id });
const chat = (id: string): Item => ({ kind: 'session', id });
/** Each pane's items by key, the active one marked with `*`. */
const panes = () => workspace.panes.map((p) => p.items.map((i) => (itemKey(i) === p.active ? '*' : '') + itemKey(i)));

beforeEach(() => {
	workspace.reset();
	workspace.onScreen = false;
	sessionView.selected = null;
	vi.mocked(goto).mockClear();
});

describe('following an item', () => {
	it('reveals it where it is open, at the new place, and focuses that pane', () => {
		workspace.openIn(doc('drafting/main.tex'), 0);
		workspace.beside(node('sy-9999'), 0);
		follow({ kind: 'document', id: 'drafting/main.tex', anchor: 'sec-2' }, 1);
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*node:sy-9999']]);
		expect(workspace.focus).toBe(0);
		expect(workspace.active(0)?.anchor).toBe('sec-2');
	});

	it('opens what is not open in the other pane, making it with one pane', () => {
		workspace.openIn(doc('drafting/main.tex'), 0);
		follow(node('sy-9999'), 0);
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*node:sy-9999']]);
		expect(workspace.focus).toBe(1);
		follow(node('sy-0003/proof'), 1);
		expect(panes()).toEqual([['document:drafting/main.tex', '*node:sy-0003/proof'], ['*node:sy-9999']]);
		expect(workspace.focus).toBe(0);
	});

	it('opens a link outside every pane in the focused pane, never splitting', () => {
		workspace.openIn(doc('drafting/main.tex'), 0);
		follow(node('sy-9999'), -1);
		expect(panes()).toEqual([['document:drafting/main.tex', '*node:sy-9999']]);
	});

	it('reveals a node in an open document that holds it, given the manifest; without it, opens the node', () => {
		workspace.openIn(doc('drafting/main.tex'), 0);
		follow(node('sy-0003'), 0, m);
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
		expect(workspace.active(0)?.anchor).toBe('sy-0003');
		follow(node('sy-0003'), 0);
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*node:sy-0003']]);
	});
});

describe('one session on screen', () => {
	it('closes every other session in both panes, and a pane left empty', () => {
		workspace.openIn(doc('drafting/main.tex'), 0);
		workspace.openIn(chat('s-a'), 0);
		workspace.beside(chat('s-b'), 0);
		workspace.openIn(chat('s-keep'), 1);
		soleSession('s-keep');
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*session:s-keep']]);
		soleSession('s-other');
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
	});
});

describe('opening a Chat', () => {
	it('outside reading mode only selects the session', () => {
		openChat('s-2026-09-16-0001', m);
		expect(sessionView.selected).toBe('s-2026-09-16-0001');
		expect(workspace.panes).toEqual([]);
	});

	it('into an empty workspace opens it where the reader is', () => {
		workspace.onScreen = true;
		openChat('s-2026-09-16-0001', m);
		expect(panes()).toEqual([['*session:s-2026-09-16-0001']]);
	});

	it('opens beside what is being read and gives focus back to the reader’s pane', () => {
		workspace.onScreen = true;
		workspace.openIn(doc('drafting/main.tex'), 0);
		openChat('s-2026-09-16-0001', m);
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*session:s-2026-09-16-0001']]);
		expect(workspace.focus).toBe(0);
		// a reader in the right-hand pane: the Chat goes left, and focus stays right
		workspace.reset();
		workspace.openIn(doc('drafting/main.tex'), 0);
		workspace.beside(node('sy-9999'), 0);
		openChat('s-2026-09-16-0001', m);
		expect(panes()).toEqual([['document:drafting/main.tex', '*session:s-2026-09-16-0001'], ['*node:sy-9999']]);
		expect(workspace.focus).toBe(1);
	});

	it('replaces the Chat of another session, and leaves the selection to a caller that set it', () => {
		workspace.onScreen = true;
		workspace.openIn(doc('drafting/main.tex'), 0);
		workspace.beside(chat('s-old'), 0);
		sessionView.selected = 's-chosen';
		openChat('s-2026-09-16-0001', m, false);
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*session:s-2026-09-16-0001']]);
		expect(sessionView.selected).toBe('s-chosen');
	});
});

describe('the link listener', () => {
	type Click = Partial<Pick<MouseEvent, 'defaultPrevented' | 'button' | 'metaKey' | 'ctrlKey' | 'shiftKey' | 'altKey'>>;
	let listeners: ((e: MouseEvent) => void)[];
	let reading: boolean;
	let manifest: Manifest | null;
	let remove: () => void;

	/** A stand-in `<a>` in pane `pane` (-1 for outside every pane): what the listener reads of the element it finds. */
	function anchor(href: string, pane = 0, attrs: { target?: string; download?: boolean } = {}) {
		const holder = pane >= 0 ? { dataset: { pane: String(pane) } } : null;
		const a = {
			target: attrs.target ?? '',
			getAttribute: (n: string) => (n === 'href' ? href : null),
			hasAttribute: (n: string) => n === 'download' && !!attrs.download,
			closest: (sel: string) => (sel === 'a' ? a : sel === '[data-pane]' ? holder : null)
		};
		return a;
	}

	/** Click a stand-in anchor; the event, whose `preventDefault` is a spy. */
	function click(a: ReturnType<typeof anchor>, over: Click = {}) {
		const e = { defaultPrevented: false, button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false, target: a, preventDefault: vi.fn(), ...over };
		for (const l of listeners) l(e as unknown as MouseEvent);
		return e;
	}

	beforeEach(() => {
		listeners = [];
		reading = true;
		manifest = m;
		vi.stubGlobal('document', {
			addEventListener: (_: string, l: (e: MouseEvent) => void, capture: boolean) => capture && listeners.push(l),
			removeEventListener: (_: string, l: (e: MouseEvent) => void) => (listeners = listeners.filter((x) => x !== l))
		});
		vi.stubGlobal('location', { href: 'http://x/master/main', origin: 'http://x' });
		remove = interceptLinks(() => reading, () => manifest);
		workspace.openIn(doc('drafting/main.tex'), 0);
	});
	afterEach(() => {
		remove();
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});

	it('is one capture-phase listener, and its removal takes it away', () => {
		expect(listeners).toHaveLength(1);
		remove();
		expect(listeners).toHaveLength(0);
	});

	it('leaves modifier clicks, other buttons, new-tab and download links and handled clicks to the browser', () => {
		const passes: [string, ReturnType<typeof anchor>, Click][] = [
			['meta', anchor('quilt:sy-9999'), { metaKey: true }],
			['ctrl', anchor('quilt:sy-9999'), { ctrlKey: true }],
			['shift', anchor('quilt:sy-9999'), { shiftKey: true }],
			['alt', anchor('quilt:sy-9999'), { altKey: true }],
			['middle button', anchor('quilt:sy-9999'), { button: 1 }],
			['already handled', anchor('quilt:sy-9999'), { defaultPrevented: true }],
			['target=_blank', anchor('quilt:sy-9999', 0, { target: '_blank' }), {}],
			['download', anchor('quilt:sy-9999', 0, { download: true }), {}]
		];
		for (const [what, a, over] of passes) expect(click(a, over).preventDefault, what).not.toHaveBeenCalled();
		manifest = null;
		expect(click(anchor('quilt:sy-9999')).preventDefault, 'no manifest yet').not.toHaveBeenCalled();
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
		expect(goto).not.toHaveBeenCalled();
	});

	it('follows a quilt: link or a viewer path in reading mode by the one rule', () => {
		expect(click(anchor('quilt:sy-9999')).preventDefault).toHaveBeenCalled();
		expect(panes()).toEqual([['*document:drafting/main.tex'], ['*node:sy-9999']]);
		expect(click(anchor('/node/sy-0042', 1)).preventDefault).toHaveBeenCalled();
		expect(panes()).toEqual([['document:drafting/main.tex', '*node:sy-0042'], ['*node:sy-9999']]);
		expect(goto).not.toHaveBeenCalled();
	});

	it('never lets a quilt: link navigate the browser, even one that names nothing', () => {
		expect(click(anchor('quilt:')).preventDefault).toHaveBeenCalled();
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
		expect(goto).not.toHaveBeenCalled();
	});

	it('outside reading mode sends a quilt: link to its item’s page and leaves the router its own paths', () => {
		reading = false;
		expect(click(anchor('quilt:sy-9999')).preventDefault).toHaveBeenCalled();
		expect(goto).toHaveBeenCalledWith('/node/sy-9999');
		expect(click(anchor('/node/sy-9999')).preventDefault).not.toHaveBeenCalled();
		expect(goto).toHaveBeenCalledTimes(1);
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
	});

	it('reveals a jump within the text as the same item at the new place; outside every pane it is the browser’s', () => {
		expect(click(anchor('#sec%202')).preventDefault).toHaveBeenCalled();
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
		expect(workspace.active(0)?.anchor).toBe('sec 2');
		expect(click(anchor('#sec-3', -1)).preventDefault).not.toHaveBeenCalled();
		expect(workspace.active(0)?.anchor).toBe('sec 2');
	});

	it('opens the modal for a cited: link with no copy on file', () => {
		const open = vi.spyOn(pdf, 'open').mockImplementation(() => {});
		expect(click(anchor('cited:arxiv:math/9810166v2?page=3')).preventDefault).toHaveBeenCalled();
		expect(open).toHaveBeenCalledWith({ id: 'arxiv:math/9810166v2', page: 3 });
		expect(panes()).toEqual([['*document:drafting/main.tex']]);
	});
});
