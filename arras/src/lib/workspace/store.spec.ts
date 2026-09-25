import { beforeEach, describe, expect, it } from 'vitest';
import { itemFromPath, itemKey, pathFor, type Item } from './item';
import { Workspace } from './store.svelte';

const m = {
	masters: [{ path: 'drafting/main.tex' }, { path: 'drafting/talk.tex' }],
	canon: [{ path: 'canon/flows-v2.tex' }]
};

const doc = (id: string, anchor?: string): Item => ({ kind: 'document', id, ...(anchor ? { anchor } : {}) });
const work = (id: string): Item => ({ kind: 'work', id });

describe('an item and its address', () => {
	it('round-trips every kind, with its place', () => {
		for (const href of [
			'/master/main#sy-0200',
			'/master/main?review=sy-0001&cause=0#sy-0001',
			'/canon/flows-v2',
			'/library/Kre99?page=4&result=Kre99-thm-2.1&view=digest',
			'/library/Kre99?page=1&quote=Artin+stacks',
			'/node/sy-0002/proof',
			'/node/sy-0002?note=a-2026-09-16-0001',
			'/master/main?note=a-2026-09-16-0004',
			'/context/sy-0002',
			'/session/s-2026-09-16-0001',
			'/session/s-2026-09-16-0001?view=did'
		]) {
			const item = itemFromPath(m, href)!;
			expect(item, href).not.toBeNull();
			expect(pathFor(m, item)).toBe(href);
		}
	});

	it('resolves a stem to the document it names, and tells a landmark from a draft', () => {
		expect(itemFromPath(m, '/master/main')).toEqual({ kind: 'document', id: 'drafting/main.tex' });
		expect(itemFromPath(m, '/canon/flows-v2')).toEqual({ kind: 'document', id: 'canon/flows-v2.tex' });
	});

	it('names nothing for a route that is not something to read', () => {
		for (const href of ['/', '/graph', '/review?show=all', '/library']) expect(itemFromPath(m, href)).toBeNull();
	});

	it('is one item whatever its place, so a place never makes a second tab', () => {
		expect(itemKey(itemFromPath(m, '/library/Kre99?page=4')!)).toBe(itemKey(itemFromPath(m, '/library/Kre99?view=info')!));
	});
});

describe('the workspace', () => {
	let w: Workspace;
	beforeEach(() => (w = new Workspace()));

	it('opens a panel choice in the focused pane and never splits for it (S4)', () => {
		w.here(doc('drafting/main.tex'));
		w.here(doc('drafting/talk.tex'));
		expect(w.panes).toHaveLength(1);
		expect(w.panes[0].items).toHaveLength(2);
		expect(w.current?.id).toBe('drafting/talk.tex');
	});

	it('opens a link beside, keeping the pane it was followed from (W7)', () => {
		w.here(doc('drafting/main.tex'));
		w.beside(work('Kre99'), 0);
		expect(w.panes).toHaveLength(2);
		expect(w.active(0)?.id).toBe('drafting/main.tex');
		expect(w.active(1)?.id).toBe('Kre99');
		expect(w.focus).toBe(1);
		// a link in the second pane opens in the first
		w.beside(doc('drafting/talk.tex'), 1);
		expect(w.active(0)?.id).toBe('drafting/talk.tex');
		expect(w.panes[0].items).toHaveLength(2);
	});

	it('opens an item once, revealing it where it already is (W8)', () => {
		w.here(doc('drafting/main.tex'));
		w.beside(work('Kre99'), 0);
		w.focusOn(0);
		w.here({ kind: 'work', id: 'Kre99', place: { page: 3 } });
		expect(w.panes[0].items).toHaveLength(1);
		expect(w.focus).toBe(1);
		expect(w.active(1)?.place).toEqual({ page: 3 });
	});

	it('stamps a reveal, so a renderer goes to the place again even when it is unchanged', () => {
		w.here(doc('drafting/main.tex', 'sy-0200'));
		const first = w.current!.seq;
		w.here(doc('drafting/main.tex', 'sy-0200'));
		expect(w.current!.seq).toBeGreaterThan(first!);
	});

	it('moves a tab to the other pane and focus follows; a pane left empty closes (W6)', () => {
		w.here(doc('drafting/main.tex'));
		w.here(doc('drafting/talk.tex'));
		w.move(0, itemKey(doc('drafting/talk.tex')));
		expect(w.panes).toHaveLength(2);
		expect(w.focus).toBe(1);
		w.move(1, itemKey(doc('drafting/talk.tex')));
		expect(w.panes).toHaveLength(1);
		expect(w.panes[0].items.map((i) => i.id)).toEqual(['drafting/main.tex', 'drafting/talk.tex']);
		expect(w.focus).toBe(0);
	});

	it('will not move the lone tab of a lone pane (W5)', () => {
		w.here(doc('drafting/main.tex'));
		w.move(0, itemKey(doc('drafting/main.tex')));
		expect(w.panes).toHaveLength(1);
	});

	it('closes a tab to its neighbour, and closes a pane left empty', () => {
		w.here(doc('drafting/main.tex'));
		w.here(doc('drafting/talk.tex'));
		w.beside(work('Kre99'), 0);
		w.close(0, itemKey(doc('drafting/talk.tex')));
		expect(w.active(0)?.id).toBe('drafting/main.tex');
		w.close(1, itemKey(work('Kre99')));
		expect(w.panes).toHaveLength(1);
		expect(w.focus).toBe(0);
	});

	it('writes the two active items to the URL, and a load reproduces them', () => {
		w.here(doc('drafting/main.tex', 'sy-0200'));
		w.beside({ kind: 'work', id: 'Arden24', place: { page: 2 } }, 0);
		const url = w.canonical(m);
		expect(url).toBe('/master/main?beside=%2Flibrary%2FArden24%3Fpage%3D2#sy-0200');
		const fresh = new Workspace();
		fresh.apply(m, url);
		expect(fresh.active(0)?.id).toBe('drafting/main.tex');
		expect(fresh.active(0)?.anchor).toBe('sy-0200');
		expect(fresh.active(1)).toMatchObject({ kind: 'work', id: 'Arden24', place: { page: 2 } });
		expect(fresh.focus).toBe(0);
	});

	it('takes a URL from outside into the focused pane when something is already open', () => {
		w.here(doc('drafting/main.tex'));
		w.beside(work('Kre99'), 0);
		w.apply(m, '/node/sy-0003');
		expect(w.active(1)?.id).toBe('sy-0003');
		expect(w.panes[1].items).toHaveLength(2);
	});

	it('keeps state for an item until its last tab closes', () => {
		w.here(work('Kre99'));
		const s = w.stateOf(itemKey(work('Kre99')), () => ({ n: 1 }));
		expect(w.stateOf(itemKey(work('Kre99')), () => ({ n: 2 }))).toBe(s);
		w.close(0, itemKey(work('Kre99')));
		expect(w.stateOf(itemKey(work('Kre99')), () => ({ n: 2 })).n).toBe(2);
	});
});
