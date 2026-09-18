// The performance probe, against a real corpus rather than the conformance fixture: 145 nodes and a 448 KB manifest,
// which is the scale the complaint is about. The fixture has twelve formulas and could never show a slow page.
import { defineConfig } from '@playwright/test';

const QUILT = process.env.PERF_BUILD ?? '';

export default defineConfig({
	webServer: {
		command: `node scripts/stage-fixture.mjs ${QUILT} && vite build && vite preview --port 4179`,
		port: 4179,
		reuseExistingServer: false,
		timeout: 240000
	},
	testDir: 'tests/perf',
	testMatch: '**/*.e2e.ts',
	workers: 1,
	use: { baseURL: 'http://localhost:4179' }
});
