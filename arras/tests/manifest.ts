// The conformance fixture's manifest, and the fakes the default suite builds on it: an edited copy served in its place, a session's Chat holding a message, and a paper filed where the fixture files none.

import type { Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

/** The fixture's manifest as committed; a test that edits it edits a copy (`serve`). */
export const manifest: any = JSON.parse(readFileSync('tests/fixture/manifest.json', 'utf8'));

/** The fixture's open session, titled `referee`. */
export const REFEREE = 's-2026-09-16-0001';

/** The fixture's closed session, titled `quick`. */
export const QUICK = 's-2026-09-15-0001';

/** Serve the fixture with `edit` applied to a copy of its manifest. */
export async function serve(page: Page, edit: (m: typeof manifest) => void): Promise<void> {
	await page.route('**/build/manifest.json', async (route) => {
		const m = structuredClone(manifest);
		edit(m);
		await route.fulfill({ json: m });
	});
}

/** The referee session's Chat, holding one message whose body is `html`. The fixture's transcript fits on its first page, which is the page served. */
export async function saying(page: Page, html: string): Promise<void> {
	await page.route(`**/build/transcripts/${REFEREE}/1.json`, (route) =>
		route.fulfill({ json: { session: REFEREE, page: 1, events: [{ seq: 1, kind: 'message', who: 'Referee Agent', when: '2026-09-16T10:00:00Z', body: '…', body_html: html }] } })
	);
}

/** The smallest PDF a browser accepts: one letter-sized page, so a work has something real to load and draw. */
export const PDF = `%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
trailer<</Root 1 0 R>>
%%EOF`;

/** Answer every filed paper with `PDF`; the manifest must also say the paper is filed (`artifacts.pdf`), which `serve` does. */
export async function servePapers(page: Page): Promise<void> {
	await page.route('**/paper.pdf', (route) => route.fulfill({ body: PDF, contentType: 'application/pdf' }));
}
