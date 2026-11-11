import { describe, expect, it } from 'vitest';
import type { Manifest } from '$lib/manifest/types';
import { compileError, compileWord, compiles, type Compile } from '$lib/manifest/compiles.svelte';
import { itemFromPath, pathFor } from './item';
import { pdfName } from './names';

// A document's compiled PDF (plan 0.29.1): an item of its own, addressed by its document's name, and how its compile stands in a word.
const m = { masters: [{ path: 'paper/main.tex' }, { path: 'notes/main.tex' }, { path: 'talk.tex' }] } as unknown as Manifest;

describe("a document's compiled PDF", () => {
	it('is addressed at /pdf/ by its document\'s name, and read back as that document', () => {
		const item = { kind: 'pdf' as const, id: 'paper/main.tex' };
		expect(pathFor(m, item)).toBe('/pdf/paper/main');
		expect(itemFromPath(m, '/pdf/paper/main')).toEqual(item);
		expect(itemFromPath(m, '/pdf/paper/main#page=3')).toEqual({ ...item, anchor: 'page=3' });
	});

	it("is named by its document and never by a file name an author's own PDF may have: by path only where two documents share a file name", () => {
		expect(pdfName(m.masters, 'talk.tex')).toBe('talk.tex · PDF');
		expect(pdfName(m.masters, 'paper/main.tex')).toBe('paper/main.tex · PDF');
	});
});

describe('how a compile stands', () => {
	const last = (result: 'ok' | 'errors' | 'failed') => ({ result, ended: 'now', error: result === 'ok' ? null : '! Undefined control sequence.', at: result === 'ok' ? null : 'l.12 \\hlind' });
	const c = (state: Compile['state'], result?: 'ok' | 'errors' | 'failed'): Compile => ({ state, again: false, last: result ? last(result) : null });

	it('says nothing of a compile that went well, and says what is under way or what went wrong', () => {
		expect(compileWord(undefined)).toBe('');
		expect(compileWord(c('idle', 'ok'))).toBe('');
		expect(compileWord(c('compiling', 'failed'))).toBe('compiling');
		expect(compileWord(c('queued'))).toBe('waiting to compile');
		expect(compileWord(c('idle', 'failed'))).toBe('did not compile');
		expect(compileWord(c('idle', 'errors'))).toBe('compiled with errors');
		expect(compileError(c('idle', 'failed'))).toBe('! Undefined control sequence. at l.12 \\hlind');
		expect(compileError(c('idle', 'ok'))).toBe('');
	});

	it('takes what the stream says, and keeps what it had when the stream says nothing it can read', () => {
		compiles.take(JSON.stringify({ 'paper/main.tex': c('compiling') }));
		expect(compiles.all['paper/main.tex'].state).toBe('compiling');
		compiles.take('not json');
		compiles.take('[1, 2]');
		expect(compiles.all['paper/main.tex'].state).toBe('compiling');
	});
});
