// The reading suite (plan 0.13 §11): the paper open under `loom serve` on a copy of the showcase — the one quilt in the repository that carries a PDF — so that annotating by selection and by box, the marks, the boxes over the page and the lit locator are all exercised against the publisher that maps them, which the fixture-only suite cannot.
//
// There is no webServer: tests/served.ts serves each test that writes on its own copy of the showcase, taken from what git tracks, and the tests that only read on one copy per worker.
import { defineConfig } from '@playwright/test';
import { results, scratch } from './tests/sites';

export default defineConfig({
	outputDir: results('reading'),
	globalSetup: './tests/served-setup.ts',
	metadata: { quilt: 'showcase', scratch: scratch('reading') },
	testDir: 'tests/e2e-reading',
	testMatch: '**/*.e2e.ts',
	fullyParallel: true,
	// 15 s rather than 5: a page PDF.js draws under a real publisher settles slowly while other suites share the machine
	expect: { timeout: 15000 },
	workers: 4,
	// tall enough that a page of a paper at the default zoom is mostly in view: a drag on a point the scroll column has clipped lands on whatever is drawn there instead, which is what the box test first found
	use: { viewport: { width: 1440, height: 900 } }
});
