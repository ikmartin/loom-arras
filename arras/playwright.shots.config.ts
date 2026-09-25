// The screenshot run of book 15.9: the same fixture as the end-to-end suite, one worker, a fixed viewport, no retries.
import { defineConfig } from '@playwright/test';
import { results, site } from './tests/sites';

const { webServer, baseURL } = site('shots', 'tests/fixture');

export default defineConfig({
	outputDir: results('shots'),
	webServer,
	testDir: 'tests/shots',
	testMatch: '**/*.spec.ts',
	workers: 1,
	use: { baseURL }
});
