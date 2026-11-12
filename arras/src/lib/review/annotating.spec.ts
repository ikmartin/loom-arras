import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import type { Annotation, Manifest } from '$lib/manifest/types';
import { authors, changedFrom, commentSeed, earlier, handPayload, hintFor, keepLook, typesPayload, isTodo, lookOf, notesHere, notesIn, passes, plain, PLAIN, quoted, retype, sequence, takeSeed, withLook, withType } from './annotating.svelte';

const fixture = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8')) as Manifest;
const RED = { color: 'red', style: 'highlight' as const, weight: 2, opacity: 65 };

/** A manifest row made by hand: what a test names, over an open untyped annotation by the reader on sy-0001. */
function row(over: Partial<Annotation> & { id: string }): Annotation {
	return {
		author: { kind: 'person', id: 'The synthetic quilt' },
		created: '2026-11-12',
		target: { key: 'sy-0001', hash: 'sha256:x' },
		type: null,
		look: { ...PLAIN },
		body_html: '',
		status: 'open',
		in_reply_to: null,
		anchored: true,
		detached: false,
		...over
	};
}

describe('the look in hand', () => {
	const held = (type: string | null, over = {}, plain = {}) => ({ type, over, plain });

	it('is its type’s look under what is set over it, or with Plain the quilt’s plain look under what is set over that', () => {
		expect(lookOf(fixture, held('revision'))).toEqual(RED);
		expect(lookOf(fixture, held('revision', { color: 'blue' }))).toEqual({ ...RED, color: 'blue' });
		expect(lookOf(fixture, held(null))).toEqual(PLAIN);
		expect(lookOf(fixture, held(null, {}, { color: 'green' }))).toEqual({ ...PLAIN, color: 'green' });
		// the quilt's own plain look, where it sets one
		expect(lookOf({ ...fixture, annotation_plain: RED }, held(null))).toEqual(RED);
		// a type the quilt no longer has draws as Plain
		expect(lookOf(fixture, held('gone', {}, { style: 'strike' }))).toEqual({ ...PLAIN, style: 'strike' });
	});

	it('keeps a field set only where it differs from the look under it, so a hand that matches its type, or the plain look, follows it', () => {
		const h = withLook(fixture, held('revision', { color: 'blue' }), { color: 'red' });
		expect(h.over).toEqual({});
		expect(withLook(fixture, h, { weight: 4 }).over).toEqual({ weight: 4 });
		const p = withLook(fixture, held(null), { color: 'green' });
		expect(p).toEqual(held(null, {}, { color: 'green' }));
		expect(withLook(fixture, p, { color: PLAIN.color }).plain).toEqual({});
	});

	it('takes a type’s own look with the type, and Plain’s own look with Plain, whatever was held between', () => {
		const p = held(null, {}, { color: 'green' });
		const q = withType(fixture, p, 'question');
		expect(q).toEqual(held('question', {}, { color: 'green' }));
		expect(lookOf(fixture, q).color).toBe('blue');
		const back = withType(fixture, withLook(fixture, q, { weight: 3 }), null);
		expect(lookOf(fixture, back)).toEqual({ ...PLAIN, color: 'green' });
	});

	it('writes its type and only the look it sets, so what it leaves follows the type or the plain look', () => {
		expect(handPayload(fixture, held('revision'))).toEqual({ type: 'revision' });
		expect(handPayload(fixture, held('revision', { opacity: 40 }))).toEqual({ type: 'revision', look: { opacity: 40 } });
		expect(handPayload(fixture, held(null))).toEqual({});
		expect(handPayload(fixture, held(null, {}, { color: 'green' }))).toEqual({ look: { color: 'green' } });
	});

	it('gives an annotation a type, or Plain, by dropping its own look; keeping the look is a choice of its own', () => {
		const a = row({ id: 'x', type: 'question', look: { ...PLAIN, color: 'pink' } });
		expect(retype(fixture, a, 'revision')).toEqual({ type: 'revision', look: null });
		expect(retype(fixture, a, null)).toEqual({ type: null, look: null });
		expect(keepLook(a)).toEqual({ type: null, look: a.look });
	});

	it('says what an annotation’s look was changed from only while its type is the quilt’s and the look differs', () => {
		expect(changedFrom(fixture, { type: 'revision', look: RED })).toBeNull();
		expect(changedFrom(fixture, { type: 'revision', look: { ...RED, color: 'blue' } })?.name).toBe('Revision');
		expect(changedFrom(fixture, { type: 'gone', look: RED })).toBeNull();
		expect(changedFrom(fixture, { type: null, look: RED })).toBeNull();
	});

	it('writes every type for types-save, one with a new look', () => {
		const saved = typesPayload(fixture, 'question', { ...RED, color: 'green' });
		expect(saved.map((t) => t.id)).toEqual(['revision', 'suggestion', 'question', 'note']);
		expect(saved[2]).toMatchObject({ id: 'question', name: 'Question', color: 'green', style: 'highlight', weight: 2, opacity: 65, open: true, notes: false });
		expect(saved[0]).toMatchObject({ color: 'red', opacity: 65 });
	});

	it('hints what the tool in hand does, what a draft still needs, and what can be done to the annotation open', () => {
		expect(hintFor(fixture, { tool: 'annotate', open: null }, held('question'))).toBe('Annotate is on. Select text to mark it as Question. Number keys switch type, 0 for Plain. Esc stops.');
		expect(hintFor(fixture, { tool: 'annotate', open: null }, held(null))).toContain('Select text to mark it in the plain look.');
		expect(hintFor(fixture, { tool: 'annotate', open: null, marked: 'a' }, held(null))).toBe('Marked. Start typing to add a comment, or select more text.');
		expect(hintFor(fixture, { tool: 'annotate', open: null, drafting: 'annotate' }, held('question'))).toBe('Not saved yet: write the comment, then press Annotate. Esc discards it.');
		expect(hintFor(fixture, { tool: null, open: null, drafting: 'comment' }, held(null))).toContain('then press Comment');
		expect(hintFor(fixture, { tool: 'comment', open: null }, held(null))).toContain('Click where the comment should go');
		expect(hintFor(fixture, { tool: null, open: 'a' }, held(null))).toContain('Delete removes it');
		expect(hintFor(fixture, { tool: null, open: null }, held(null))).toBe('');
	});

	it('hands the keys typed at a mark to that annotation’s popup once, and to no other', () => {
		commentSeed.id = 'a';
		commentSeed.text = 'Hel';
		expect(takeSeed('b')).toBeNull();
		expect(takeSeed('a')).toBe('Hel');
		expect(takeSeed('a')).toBeNull();
	});
});

describe('the Comments list and To do', () => {
	const m = { ...fixture, reviewer: { name: 'me', source: '' } } as Manifest;
	const theirs = row({ id: 'a', type: 'question', author: { kind: 'agent', id: 'agent' } });
	const mine = row({ id: 'b', type: 'question', author: { kind: 'person', id: 'me' } });
	const informs = row({ id: 'c', type: 'note', author: { kind: 'agent', id: 'agent' } });
	const untyped = row({ id: 'd', author: { kind: 'agent', id: 'agent' } });
	const done = row({ id: 'e', type: 'question', status: 'resolved', author: { kind: 'agent', id: 'agent' } });

	it('holds in To do only open annotations of a type that stays open, from others than the reader', () => {
		expect([theirs, mine, informs, untyped, done].filter((a) => isTodo(m, a)).map((a) => a.id)).toEqual(['a']);
	});

	it('leaves out the people the filter leaves out, and the resolved unless they are shown', () => {
		const s = { hidden: ['agent'], todo: false };
		expect(passes(m, theirs, s, false)).toBe(false);
		expect(passes(m, mine, s, false)).toBe(true);
		expect(passes(m, done, { hidden: [], todo: false }, false)).toBe(false);
		expect(passes(m, done, { hidden: [], todo: false }, true)).toBe(true);
	});

	it('steps in reading order, under the filter', () => {
		const rows = Object.fromEntries([theirs, mine, informs, done].map((a) => [a.id, a]));
		const withRows = { ...m, annotations: rows } as Manifest;
		expect(sequence(withRows, { order: ['c', 'e', 'a', 'b', 'gone'], hidden: [], todo: false }, false).map((a) => a.id)).toEqual(['c', 'a', 'b']);
		expect(sequence(withRows, { order: ['c', 'e', 'a', 'b'], hidden: [], todo: true }, true).map((a) => a.id)).toEqual(['a']);
	});

	it('names the reader first among the people', () => {
		expect(authors(m, [theirs, mine]).map((p) => p.id)).toEqual(['me', 'agent']);
	});
});

describe('the Notes list', () => {
	it('holds the annotations whose type is listed in Notes, grouped by the document, work or PDF they are on', () => {
		const m = structuredClone(fixture) as Manifest;
		m.annotations = {
			n1: row({ id: 'n1', type: 'note', target: { key: 'sy-0003', hash: '' } }),
			n2: row({ id: 'n2', type: 'note', target: { key: 'drafting/figures/fig.pdf', hash: '', file: 'drafting/figures/fig.pdf', page: 1 } }),
			n3: row({ id: 'n3', type: 'note', target: { key: 'sy-0003', hash: '' }, in: 'drafting/talk.tex' }),
			q: row({ id: 'q', type: 'question', target: { key: 'sy-0003', hash: '' } }),
			r: row({ id: 'r', type: 'note', in_reply_to: 'n1' })
		};
		const groups = notesIn(m);
		expect(groups.map((g) => [g.label, g.notes.map((a) => a.id)])).toEqual([
			['main.tex', ['n1']],
			['fig.pdf', ['n2']],
			['talk.tex', ['n3']]
		]);
		// the badge on an item's toolbar counts only those read there
		expect(notesHere(m, { order: ['n1', 'q', 'r'] })).toBe(1);
	});
});

describe('written on earlier words', () => {
	it('is the words quoted and the version that holds them, for an annotation whose words are gone and whose version is kept', () => {
		const a = row({ id: 'v', detached: true, recorded: true, quote: 'an involution $\\sigma$', version: { hash: 'sha256:abc', fragment: 'fragments/versions/abc.html', at: false } });
		expect(earlier(a)).toEqual({ words: 'an involution $\\sigma$', fragment: 'fragments/versions/abc.html', at: false });
		expect(earlier(row({ id: 'w', quote: 'still here' }))).toBeNull();
		expect(earlier(row({ id: 'n', version: null }))).toBeNull();
	});

	it('reads the version loom publishes for the fixture’s question on sy-0001', () => {
		const a = fixture.annotations['a-2026-09-16-a91hwf'];
		expect(earlier(a)).toMatchObject({ words: a.quote, at: true });
		expect(earlier(a)?.fragment).toMatch(/^fragments\/versions\/.+\.html$/);
	});
});

describe('a quote and a comment', () => {
	it('quotes the words, then where they came from as a link', () => {
		expect(quoted('finite widget', 'Theorem 2.1', 'quilt:sy-0003')).toBe('> finite widget\n— [Theorem 2.1](quilt:sy-0003)');
	});

	it('reads a comment’s words without its markup', () => {
		expect(plain('<p>Is <em>this</em> &amp; that &lt;ok&gt;?</p>')).toBe('Is this & that <ok>?');
		expect(plain('<p> </p>')).toBe('');
	});
});
