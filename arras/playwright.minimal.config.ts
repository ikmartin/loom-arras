// The interface floor (plan 0.9.5 §10, §11 checks 1-2): the same app served against `tests/fixture-minimal`, a manifest written by nobody's publisher with eleven top-level sections omitted outright.
import { defineConfig } from '@playwright/test';
import { results, site } from './tests/sites';

const { webServer, baseURL } = site('minimal', 'tests/fixture-minimal');

export default defineConfig({
	outputDir: results('minimal'),
	webServer,
	testDir: 'tests/e2e-minimal',
	testMatch: '**/*.e2e.{ts,js}',
	use: { baseURL }
});
