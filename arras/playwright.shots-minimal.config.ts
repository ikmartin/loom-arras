// Screenshots of the app against the interface floor (tests/fixture-minimal), for the workspace's feature reports. Its own port, because the other three configs pin 4173 and 4176 with `reuseExistingServer: false`.
import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: {
		command: 'npm run build:fixture-minimal && npm run preview -- --port 4177',
		port: 4177,
		reuseExistingServer: false
	},
	testDir: 'tests/shots-minimal',
	testMatch: '**/*.spec.ts',
	workers: 1,
	use: { baseURL: 'http://localhost:4177' }
});
