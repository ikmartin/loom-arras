// The write API, end to end (plan 0.11 Part H): the real viewer, served by the real publisher, writing into a real
// quilt. The other three configs serve a static preview with no write API, which is the right default -- a deployed
// site has no publisher behind it -- so this is the only suite where an editing affordance exists at all.
//
// The quilt is a scratch copy, because these tests write to it. LOOM_ARRAS_BUNDLE points loom at the build under test
// rather than the one vendored into it, which would be whatever was last released.
import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: {
		command:
			'npm run build && rm -rf .tmp-write-quilt && cp -R ../loom/tests/quilts/synthetic .tmp-write-quilt && LOOM_ARRAS_BUNDLE="$PWD/build" ../loom/.venv/bin/loom serve --quilt .tmp-write-quilt --port 4178 --no-compile',
		port: 4178,
		reuseExistingServer: false,
		timeout: 180000
	},
	testDir: 'tests/e2e-write',
	testMatch: '**/*.e2e.ts',
	// shots.e2e.ts writes the committed pictures under records/images, so it runs only when asked (`npm run shots:write`)
	testIgnore: process.env.ARRAS_SHOTS ? [] : ['**/shots.e2e.ts'],
	workers: 1,
	use: { baseURL: 'http://localhost:4178' }
});
