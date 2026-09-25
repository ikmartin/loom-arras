// The reading layer's performance floor (tests/perf), against whatever corpus build `PERF_BUILD` names rather than the conformance fixture, whose papers are too few and too small to show a slow page. Run by hand: `PERF_BUILD=<quilt>/build npx playwright test --config playwright.perf.config.ts`.
import { defineConfig } from '@playwright/test';
import { results, site } from './tests/sites';

const { webServer, baseURL } = site('perf', process.env.PERF_BUILD || 'tests/fixture');

export default defineConfig({
	outputDir: results('perf'),
	webServer,
	testDir: 'tests/perf',
	testMatch: '**/*.e2e.ts',
	workers: 1,
	use: { baseURL }
});
