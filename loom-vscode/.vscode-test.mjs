import { createRequire } from 'node:module';
import * as path from 'node:path';
import { defineConfig } from '@vscode/test-cli';

// Two runs: one inside a fresh copy of loom's synthetic quilt, where everything is exercised, and one in a plain LaTeX folder, where the extension must do nothing. Both are made in a new temp dir on every run (see src/test/fixture.ts), so no run sees what an earlier one left.
// LOOM_LSP and LOOM_BIN name the executables; the extension host has its own environment and does not inherit the shell's PATH. A relative path is made absolute here, since the host does not run in this directory; a bare name is left for PATH.
const { makeWorkspaces } = createRequire(import.meta.url)('./out/test/fixture.js');
const { quilt, plain } = makeWorkspaces();
const absolute = (value) => (value && value.includes(path.sep) ? path.resolve(value) : (value ?? ''));
const env = { LOOM_LSP: absolute(process.env.LOOM_LSP), LOOM_BIN: absolute(process.env.LOOM_BIN) };

export default defineConfig([
	{
		label: 'in a quilt',
		files: ['out/test/unit.test.js', 'out/test/integration.test.js'],
		workspaceFolder: quilt,
		mocha: { timeout: 120000 },
		env
	},
	{
		label: 'outside a quilt',
		files: 'out/test/outside.test.js',
		workspaceFolder: plain,
		mocha: { timeout: 120000 },
		env
	}
]);
