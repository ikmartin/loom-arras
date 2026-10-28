import { describe, expect, it } from 'vitest';
import { FOLD_AT, split } from './fold';

const block = (name: string, text: string) => `<section data-block="${name}"><h2>${name}</h2><p>${text}</p></section>`;
const long = 'x'.repeat(FOLD_AT);

describe('a report folded after its first block', () => {
	it('shows the line naming the mode and the first block, and folds the rest', () => {
		const html = '<p>Mode: referee, on dm-0003.</p>' + block('summary', 'One objection.') + block('referee-review', long) + block('decision', 'Minor.');
		const f = split(html);
		expect(f?.head).toBe('<p>Mode: referee, on dm-0003.</p>' + block('summary', 'One objection.'));
		expect(f?.rest).toBe(block('referee-review', long) + block('decision', 'Minor.'));
		expect(f?.names).toEqual(['referee-review', 'decision']);
	});

	it('leaves a message whole when it has one block or none, or a short tail', () => {
		expect(split('<p>Done.</p>')).toBeNull();
		expect(split(block('answer', long))).toBeNull();
		expect(split(block('summary', 'Short.') + block('decision', 'Minor.'))).toBeNull();
	});

	it('counts the text of the folded part, not its markup', () => {
		const tags = '<p></p>'.repeat(400);
		expect(split(block('summary', 'S') + `<section data-block="rejected"><h2>rejected</h2>${tags}</section>`)).toBeNull();
	});
});
