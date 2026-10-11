// The viewer's speed under a running publisher, on a large real paper: the divider, re-renders, an agent's annotations arriving, the graph, a PDF. Run by hand, since it needs a corpus the repository does not carry: `PERF_QUILT=../demos/relloc npx playwright test --config playwright.perf-live.config.ts`. `PERF_ENFORCE=0` reports the numbers without failing on a budget, which is how a baseline is taken.
//
// Each test is served by tests/served.ts on its own copy of the quilt that tests/perf-live/setup.ts prepared once: copied from `PERF_QUILT`, seeded with a session, forty annotations and a filed PDF, and built.
import { defineConfig } from '@playwright/test';
import { results, scratch } from './tests/sites';

export default defineConfig({
	outputDir: results('perf-live'),
	globalSetup: './tests/perf-live/setup.ts',
	metadata: { quilt: 'perf', scratch: scratch('perf-live') },
	testDir: 'tests/perf-live',
	testMatch: '**/*.e2e.ts',
	timeout: 600000,
	expect: { timeout: 60000 },
	workers: 1,
	use: { viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 }
});
