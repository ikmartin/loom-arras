import { describe, expect, it } from 'vitest';
import { asPercent } from './document';

describe('a rectangle on a page', () => {
	it('is placed from the top, because the publisher measures from the top', () => {
		// The incident: the span's docstring said "PDF user space", whose origin is the bottom left. It is not — the
		// coordinates are what `pdftotext -bbox-layout` emits, points from the top left. A viewer that believed the
		// docstring drew every highlight mirrored about the middle of the page.
		const at = asPercent([61.2, 79.2, 306, 158.4], { width: 612, height: 792 });
		expect(at).toEqual({ left: '10%', top: '10%', width: '40%', height: '10%' });
	});

	it('is a fraction of its own page, so a page of another size is still right', () => {
		// Pages of one scan differ by a point or two, so the box is per page and never per document.
		const at = asPercent([0, 403, 533, 806], { width: 533, height: 806 });
		expect(at).toEqual({ left: '0%', top: '50%', width: '100%', height: '50%' });
	});
});
