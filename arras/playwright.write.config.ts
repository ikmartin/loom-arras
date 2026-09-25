// The write API, end to end (plan 0.11 Part H): the real viewer, served by the real publisher, writing into a real quilt. The other configs serve a static preview with no write API, which is the right default -- a deployed site has no publisher behind it -- so this is the only suite where an editing affordance exists at all.
//
// There is no webServer: each test is served by the fixture in tests/served.ts, on its own copy of the synthetic quilt taken from what git tracks, so no test sees another's writes. LOOM_ARRAS_BUNDLE points loom at the build under test rather than the one vendored into it, which would be whatever was last released. The suite runs whatever `../loom/.venv/bin/loom` is installed.
import { defineConfig } from '@playwright/test';
import { results, scratch } from './tests/sites';

export default defineConfig({
	outputDir: results('write'),
	globalSetup: './tests/served-setup.ts',
	metadata: { quilt: 'synthetic', scratch: scratch('write') },
	testDir: 'tests/e2e-write',
	testMatch: '**/*.e2e.ts',
	// shots.e2e.ts writes the committed pictures under records/images, so it runs only when asked (`npm run shots:write`)
	testIgnore: process.env.ARRAS_SHOTS ? [] : ['**/shots.e2e.ts'],
	fullyParallel: true,
	// 15 s rather than 5: a page PDF.js draws under a real publisher settles slowly while other suites share the machine
	expect: { timeout: 15000 },
	workers: 4
});
