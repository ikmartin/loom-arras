import { describe, expect, it } from 'vitest';
import { accessOf, accessOfAll, explain, says } from './access';
import type { ProjectFile } from '$lib/manifest/types';

const file = (path: string, denied: ProjectFile['denied'] = null): ProjectFile => ({ path, kind: 'document', bytes: 1, ...(denied === undefined ? {} : { denied }) });
const unsaid = (path: string): ProjectFile => ({ path, kind: 'document', bytes: 1 });
const listed = { by: 'drafting/', always: false };

describe('who edits a row', () => {
	it('is the publisher\'s word per file: a file it denies agents is the person\'s alone, any other is theirs and the agents\'', () => {
		expect(accessOf(file('drafting/main.tex', listed))).toEqual({ agents: false, by: 'drafting/', always: false });
		expect(accessOf(file('notes/a.tex'))).toEqual({ agents: true });
	});

	it('is nothing where the publisher does not say, so silence is never read as permission', () => {
		expect(accessOf(unsaid('notes/a.tex'))).toBeNull();
		expect(accessOfAll([file('d/a.tex'), unsaid('d/b.tex')])).toBeNull();
		expect(says([unsaid('a.tex')])).toBe(false);
		expect(says([unsaid('a.tex'), file('b.tex')])).toBe(true);
		expect(says(undefined)).toBe(false);
	});

	it("is a directory's when every file beneath it agrees, keeping a reason they share, and none when they differ", () => {
		expect(accessOfAll([file('d/a.tex', listed), file('d/b.tex', listed)])).toEqual({ agents: false, by: 'drafting/', always: false });
		expect(accessOfAll([file('d/a.tex', listed), file('d/b.tex', { by: '*.bib', always: false })])).toEqual({ agents: false });
		expect(accessOfAll([file('d/a.tex'), file('d/b.tex')])).toEqual({ agents: true });
		expect(accessOfAll([file('d/a.tex'), file('d/b.tex', listed)])).toBeNull();
		expect(accessOfAll([])).toBeNull();
	});

	it('says what each mark means, pointing to Settings for the list and naming the document a copy goes back to', () => {
		expect(explain({ agents: false, by: 'drafting/', always: false }, {}).body).toBe('drafting/ is on the list of where agents may not write, in Settings › Agents.');
		expect(explain({ agents: false, by: 'config.toml', always: true }, {}).body).toBe("No agent writes the quilt's configuration.");
		expect(explain({ agents: false, by: 'research-state.md', always: true }, { statePath: 'research-state.md' }).title).toBe('Agents change this only through loom');
		expect(explain({ agents: false }, { dir: true }).title).toBe('Only you edit what is in here');
		expect(explain({ agents: true }, { copyOf: 'drafting/examples.tex' }).body).toContain('back to examples.tex through Review › Proposed to you');
		// Review › Your text follows text files only, so a PDF an agent may replace is not promised there
		expect(explain({ agents: true }, { kind: 'pdf' }).body).toBe('An agent may change or replace this file.');
		expect(explain({ agents: true }, { kind: 'markdown' }).body).toContain('Review › Your text');
	});
});
