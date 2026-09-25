// Screenshots of the app against the interface floor (tests/fixture-minimal), for the workspace's feature reports.
import { defineConfig } from '@playwright/test';
import { results, site } from './tests/sites';

const { webServer, baseURL } = site('shots-minimal', 'tests/fixture-minimal');

export default defineConfig({
	outputDir: results('shots-minimal'),
	webServer,
	testDir: 'tests/shots-minimal',
	testMatch: '**/*.spec.ts',
	workers: 1,
	use: { baseURL }
});
