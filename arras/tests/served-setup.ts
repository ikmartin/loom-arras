// Global setup for the write and reading suites: stage the suite's copy of the app once, and copy the config's quilt once from what git tracks, so untracked files in loom's working tree never reach a test, then build that copy. Each test's copy is taken from this pristine one (served.ts).

import type { FullConfig } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { ARRAS, LOOM, scratchDir, suiteOf } from './served';

export default function setup(config: FullConfig): void {
	const suite = suiteOf({ config });
	const dir = scratchDir(suite);
	rmSync(dir, { recursive: true, force: true });
	// the suite's own copy of the app, which LOOM_ARRAS_BUNDLE points every server at: ARRAS_PREBUILT's, or a fresh build's
	try {
		execFileSync(process.execPath, [join(ARRAS, 'scripts', 'bundle.mjs'), join(dir, 'bundle')], { cwd: ARRAS, stdio: 'pipe' });
	} catch (err) {
		throw new Error(`scripts/bundle.mjs failed:\n${(err as { stdout?: Buffer }).stdout}\n${(err as { stderr?: Buffer }).stderr}`);
	}
	const repo = join(ARRAS, '..');
	const prefix = `loom/tests/quilts/${suite.quilt}/`;
	const tracked = execFileSync('git', ['ls-files', '-z', '--', prefix], { cwd: repo }).toString().split('\0').filter(Boolean);
	if (!tracked.length) throw new Error(`git tracks nothing under ${prefix}`);
	for (const file of tracked) {
		// a tracked file deleted in the working tree is copied as the working tree has it: absent
		if (!existsSync(join(repo, file))) continue;
		const to = join(dir, 'template', file.slice(prefix.length));
		mkdirSync(dirname(to), { recursive: true });
		copyFileSync(join(repo, file), to);
	}
	// built once here, so each served copy starts from a warm cache; the quilt's own errors make loom exit 1, which is not a failure to build
	try {
		execFileSync(LOOM, ['build', '--quilt', join(dir, 'template')], { cwd: ARRAS, stdio: 'pipe' });
	} catch (err) {
		if ((err as { status?: number }).status !== 1) throw err;
	}
}
