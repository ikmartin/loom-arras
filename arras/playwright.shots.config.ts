// The screenshot run of book 15.9: the same built fixture as the end-to-end suite, one worker, a fixed viewport, no retries.
import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: { command: 'npm run build:fixture && npm run preview', port: 4173, reuseExistingServer: false },
	testDir: 'tests/shots',
	testMatch: '**/*.spec.ts',
	workers: 1,
	use: { baseURL: 'http://localhost:4173' }
});
