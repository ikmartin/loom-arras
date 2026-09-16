import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: { command: 'npm run build && npm run preview', port: 4173, reuseExistingServer: false },
	testDir: 'tests/e2e',
	testMatch: '**/*.e2e.{ts,js}',
	use: { baseURL: 'http://localhost:4173' }
});
