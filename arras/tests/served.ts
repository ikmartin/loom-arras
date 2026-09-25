// The write and reading suites run the real viewer against a real `loom serve`, on a copy of one of loom's committed quilts (the config's `metadata.quilt`). `test` gives each test its own copy and its own server, so what one test writes no other test sees; `readOnly` shares one per worker, for tests that write nothing. `served-setup.ts` builds the bundle and the pristine copy once per run.

import { test as base, expect, type TestInfo } from '@playwright/test';
import { spawn, execFileSync, type ChildProcess } from 'node:child_process';
import { cpSync, createWriteStream, existsSync, readFileSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

/** What a config says about its quilt, in `metadata`. */
export interface Suite {
	/** The quilt under `loom/tests/quilts/`. */
	quilt: string;
	/** Scratch directory, relative to `arras/`, for the bundle, the pristine copy and every served copy. */
	scratch: string;
}

export const ARRAS = fileURLToPath(new URL('..', import.meta.url));
export const LOOM = join(ARRAS, '../loom/.venv/bin/loom');

export type Entry = Record<string, unknown>;

/** One running `loom serve` over one quilt copy. */
export interface Served {
	/** The copy's root, absolute. */
	root: string;
	/** Where it answers, with no trailing slash. */
	url: string;
	/** The annotation log, parsed. */
	log(): Entry[];
	/** The one `created` entry whose body is exactly `body`; fails if there is not exactly one. */
	written(body: string): Entry;
	/** Open sessions, oldest first, from the copy's own session index. */
	openSessions(): string[];
	/** POST to the write API with the served token; returns the publisher's `result`, and fails on a refusal. */
	api(endpoint: string, body: Record<string, unknown>): Promise<string>;
	/** Run the loom CLI against this copy; returns stdout. */
	loom(args: string[], env?: Record<string, string>): string;
}

export function suiteOf(info: { config: { metadata: Record<string, unknown> } }): Suite {
	const { quilt, scratch } = info.config.metadata as Partial<Suite>;
	if (!quilt || !scratch) throw new Error('the config names no metadata.quilt and metadata.scratch');
	return { quilt, scratch };
}

export function scratchDir(suite: Suite): string {
	return join(ARRAS, suite.scratch);
}

function freePort(): Promise<number> {
	return new Promise((resolve, reject) => {
		const srv = createServer();
		srv.once('error', reject);
		srv.listen(0, '127.0.0.1', () => {
			const port = (srv.address() as { port: number }).port;
			srv.close(() => resolve(port));
		});
	});
}

function parseLines(path: string): Entry[] {
	return readFileSync(path, 'utf8')
		.split('\n')
		.filter((l) => l.trim())
		.map((l) => JSON.parse(l));
}

interface Running {
	served: Served;
	logPath: string;
	stop(): Promise<void>;
}

/**
 * Copy the pristine quilt to `name` and serve it on a free port until it has published its first build.
 *
 * The server is started in its own process group, so stopping it also stops an agent turn it launched. A port lost to a race with another worker shows as an early exit, and is retried on a new one. The pristine copy carries a build, so the server's first one only checks its cache.
 */
async function start(suite: Suite, name: string): Promise<Running> {
	const dir = scratchDir(suite);
	const root = join(dir, 'quilts', name);
	const logPath = `${root}.serve.log`;
	rmSync(root, { recursive: true, force: true });
	cpSync(join(dir, 'template'), root, { recursive: true });
	let lastLog = '';
	for (let attempt = 0; attempt < 3; attempt++) {
		const port = await freePort();
		const url = `http://127.0.0.1:${port}`;
		const out = createWriteStream(logPath, { flags: 'a' });
		const proc: ChildProcess = spawn(LOOM, ['serve', '--quilt', root, '--port', String(port), '--no-compile'], {
			cwd: ARRAS,
			detached: true,
			env: { ...process.env, LOOM_ARRAS_BUNDLE: join(dir, 'bundle') },
			stdio: ['ignore', 'pipe', 'pipe']
		});
		proc.stdout!.pipe(out);
		proc.stderr!.pipe(out);
		let exited = false;
		const gone = new Promise<void>((r) => proc.once('exit', () => ((exited = true), r())));
		// killed outright: a graceful stop waits out the watcher's poll, over a second per test, and the copy is thrown away after
		const stop = async () => {
			if (!exited) {
				try {
					process.kill(-proc.pid!, 'SIGKILL');
				} catch {
					/* already gone */
				}
				await gone;
			}
			out.end();
		};
		// the build directory answers 503 until the first build is done, so a manifest is the sign it is ready
		const deadline = Date.now() + 60000;
		let token = '';
		while (!exited && Date.now() < deadline) {
			try {
				const res = await fetch(`${url}/build/manifest.json`);
				if (res.ok) {
					token = ((await (await fetch(`${url}/_api`)).json()) as { token: string }).token;
					break;
				}
			} catch {
				/* not listening yet */
			}
			await new Promise((r) => setTimeout(r, 50));
		}
		if (!token) {
			await stop();
			lastLog = existsSync(logPath) ? readFileSync(logPath, 'utf8') : '';
			continue;
		}
		const served: Served = {
			root,
			url,
			log: () => parseLines(join(root, 'annotations/log.jsonl')),
			written(body) {
				const mine = served.log().filter((e) => e.event === 'created' && e.body === body);
				expect(mine, `the log's created entries with the body ${JSON.stringify(body)}`).toHaveLength(1);
				return mine[0];
			},
			openSessions() {
				const open = new Map<string, boolean>();
				for (const e of parseLines(join(root, '.loom/sessions/index.jsonl'))) {
					const id = String(e.id);
					if (e.event === 'created') open.set(id, true);
					else if (e.event === 'closed' || e.event === 'deleted') open.set(id, false);
					else if (e.event === 'resumed') open.set(id, true);
				}
				return [...open].filter(([, o]) => o).map(([id]) => id);
			},
			async api(endpoint, body) {
				const res = await fetch(`${url}/_api/${endpoint}`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json', 'X-Loom-Token': token },
					body: JSON.stringify(body)
				});
				const text = await res.text();
				expect(res.status, `POST /_api/${endpoint} answered ${text}`).toBe(200);
				return String((JSON.parse(text) as { result: unknown }).result ?? '');
			},
			loom(args, env = {}) {
				return execFileSync(LOOM, [...args, '--quilt', root], { cwd: ARRAS, env: { ...process.env, ...env } }).toString();
			}
		};
		return { served, logPath, stop };
	}
	throw new Error(`loom serve never published ${root}:\n${lastLog}`);
}

/** Keep a failed test's copy and attach its server log; remove a passing one's. */
async function finish(running: Running, info: TestInfo): Promise<void> {
	await running.stop();
	if (info.status !== info.expectedStatus) {
		await info.attach('loom serve', { path: running.logPath, contentType: 'text/plain' });
		await info.attach('quilt copy', { body: running.served.root, contentType: 'text/plain' });
		return;
	}
	rmSync(running.served.root, { recursive: true, force: true });
	rmSync(running.logPath, { force: true });
}

interface TestFixtures {
	/** Whether this test gets a copy of its own; `readOnly` sets it false. */
	ownQuilt: boolean;
	served: Served;
}

interface WorkerFixtures {
	/** The worker's shared server, started the first time a read-only test asks for it. */
	sharedServed: () => Promise<Served>;
}

export const test = base.extend<TestFixtures, WorkerFixtures>({
	ownQuilt: [true, { option: true }],
	sharedServed: [
		async ({}, use, info) => {
			let running: Promise<Running> | undefined;
			await use(async () => (await (running ??= start(suiteOf(info), `worker-${info.workerIndex}`))).served);
			if (running) await (await running).stop();
		},
		{ scope: 'worker' }
	],
	served: async ({ ownQuilt, sharedServed }, use, info) => {
		if (!ownQuilt) {
			await use(await sharedServed());
			return;
		}
		const running = await start(suiteOf(info), `${info.testId}-${info.repeatEachIndex}-${info.retry}`);
		await use(running.served);
		await finish(running, info);
	},
	baseURL: async ({ served }, use) => {
		await use(served.url);
	}
});

/** A test that writes nothing to the quilt, and so shares its worker's server. */
export const readOnly = test.extend({ ownQuilt: false });

export { expect };
