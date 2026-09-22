// The reading suite (plan 0.13 §11): the paper open under `loom serve` on a copy of the showcase — the one quilt in the
// repository that carries a PDF — so that annotating by selection and by box, the marks, the boxes over the page and
// the lit locator are all exercised against the publisher that maps them, which the fixture-only suite cannot.
import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: {
		command:
			'npm run build && rm -rf .tmp-reading-quilt && cp -R ../loom/tests/quilts/showcase .tmp-reading-quilt && LOOM_ARRAS_BUNDLE="$PWD/build" ../loom/.venv/bin/loom serve --quilt .tmp-reading-quilt --port 4177 --no-compile',
		port: 4177,
		reuseExistingServer: false,
		timeout: 180000
	},
	testDir: 'tests/e2e-reading',
	testMatch: '**/*.e2e.ts',
	workers: 1,
	// tall enough that a page of a paper at the default zoom is mostly in view: a drag on a point the scroll column
	// has clipped lands on whatever is drawn there instead, which is what the box test first found
	use: { baseURL: 'http://localhost:4177', viewport: { width: 1440, height: 900 } }
});
