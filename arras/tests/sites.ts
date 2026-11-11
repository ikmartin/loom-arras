// Where each Playwright config's copy of the app lives and which port serves it, so that any of them can run beside any other.
//
// ARRAS_SLOT (default 0) separates whole runs: slot n serves on each base port plus 100·n and keeps its copies under `.tmp-e2e/slot-n/`, so `scripts/verify`, which takes the first slot from 1 that nothing on the machine holds, meets neither a suite started by hand nor another worktree's run. ARRAS_PREBUILT is read by scripts/bundle.mjs.

import { join } from 'node:path';

const slot = Number(process.env.ARRAS_SLOT ?? 0);

/** The scratch directory for `name`, relative to `arras/`. */
export function scratch(name: string): string {
	return join('.tmp-e2e', slot ? `slot-${slot}` : '', name);
}

/** The config's own Playwright outputDir, since a run empties its outputDir as it starts and the default `test-results/` is one for all. */
export function results(name: string): string {
	return join('test-results', slot ? `slot-${slot}` : '', name);
}

/**
 * How long a suite waits before calling something failed, spread into each config: a test's whole budget, one expectation's, and how many failures end a run.
 *
 * Generous, because a machine running other suites has taken minutes over what takes seconds alone, and no suite can win CPU back from them. It costs a passing test nothing, since a wait ends as soon as the thing happens; only a failure spends it, so a run that has failed this often stops rather than spending it on every test a broken viewer would fail.
 */
export const patient = { timeout: 300000, expect: { timeout: 120000 }, maxFailures: 10 };

/** Each statically served config's base port, read by `scripts/verify`, which claims a slot on 4175, so that one stays out of this table; the write and reading suites take a free port per server instead. */
const PORTS = { e2e: 4173, shots: 4174 };

/** The webServer and baseURL of a config that serves the app statically: a copy of the build with `fixture` staged into it, under `scratch(name)`, served by scripts/serve-static.mjs on the config's port shifted by the slot. */
export function site(name: keyof typeof PORTS, fixture: string) {
	const at = PORTS[name] + 100 * slot;
	const dir = scratch(name);
	return {
		webServer: {
			command: `node scripts/bundle.mjs ${dir} ${JSON.stringify(fixture)} && node scripts/serve-static.mjs ${dir} ${at}`,
			url: `http://127.0.0.1:${at}/`,
			reuseExistingServer: false,
			timeout: 300000
		},
		baseURL: `http://127.0.0.1:${at}`
	};
}
