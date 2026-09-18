// The interface floor (plan 0.9.5 §10, §11 checks 1-2): the same app served against `tests/fixture-minimal`, a manifest
// written by nobody's publisher with eleven top-level sections omitted outright. Its own port, because the other two
// configs both pin 4173 with `reuseExistingServer: false` and would fight this one for it.
import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: {
		command: 'npm run build:fixture-minimal && npm run preview -- --port 4176',
		port: 4176,
		reuseExistingServer: false
	},
	testDir: 'tests/e2e-minimal',
	testMatch: '**/*.e2e.{ts,js}',
	use: { baseURL: 'http://localhost:4176' }
});
