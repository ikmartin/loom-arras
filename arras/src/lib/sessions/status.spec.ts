// The Chat's status line, one row per branch: what the publisher said of the agent and the listeners, and the last send, against the line a reader sees.
import { describe, expect, it } from 'vitest';
import { statusLine, type StatusInput } from './status';
import type { AgentState, Listener, Posted } from './transcript.svelte';

const SENT_AT = '2026-09-24T10:00:05Z';
const BEFORE = '2026-09-24T10:00:00Z';
const AFTER = '2026-09-24T10:00:07Z';

const referee: Listener = { who: 'Referee', kind: 'terminal' };
const ann: Listener = { who: 'Ann', kind: 'human' };
const claude = (over: Partial<AgentState> = {}): AgentState => ({ launch: true, name: 'Claude', ...over });
const posted = (attached?: Listener[]): Posted => ({ ok: true, session: 's-1', seq: 4, ...(attached ? { attached } : {}) });

const at = (over: Partial<StatusInput>): StatusInput => ({ agent: null, attached: null, sent: null, sentAt: '', ...over });

const rows: [string, StatusInput, string][] = [
	// what keeps the agent from starting outranks everything, even a turn said to be running
	['blocked', at({ agent: claude({ blocked: 'claude is not on PATH', state: 'running' }) }), 'Claude cannot be started: claude is not on PATH'],
	['blocked, unnamed', at({ agent: claude({ name: '', blocked: 'no agent configured' }) }), 'The agent cannot be started: no agent configured'],
	['running, with activity', at({ agent: claude({ state: 'running', activity: 'loom show sy-0003' }), sent: posted(), sentAt: SENT_AT }), 'Claude is working · loom show sy-0003'],
	['running, no activity yet', at({ agent: claude({ state: 'running' }), attached: [referee] }), 'Claude is working'],
	['failed since the send', at({ agent: claude({ state: 'failed', error: 'exit 2', started: AFTER }), sent: posted(), sentAt: SENT_AT }), 'Claude could not run: exit 2'],
	['failed since the send, no error given', at({ agent: claude({ state: 'failed', started: SENT_AT }), sent: posted(), sentAt: SENT_AT }), 'Claude could not run: it stopped with an error'],
	['stopped since the send', at({ agent: claude({ state: 'stopped', started: AFTER }), sent: posted(), sentAt: SENT_AT }), 'Claude was stopped'],
	// a turn that ended before the send says nothing of it: the send is still waiting for its own
	['failed before the send, will start', at({ agent: claude({ state: 'failed', error: 'exit 2', started: BEFORE }), sent: posted(), sentAt: SENT_AT }), 'sent · Claude will start'],
	['stopped before the send, nobody to start it', at({ agent: claude({ launch: false, state: 'stopped', started: BEFORE }), sent: posted(), sentAt: SENT_AT }), 'sent · it waits in the inbox'],
	['failed, no start time, after a send', at({ agent: claude({ state: 'failed' }), sent: posted(), sentAt: SENT_AT }), 'sent · Claude will start'],
	['sent, one attached', at({ agent: claude(), attached: [referee], sent: posted(), sentAt: SENT_AT }), 'sent · Referee is attached'],
	['sent, two attached', at({ attached: [referee, ann], sent: posted(), sentAt: SENT_AT }), 'sent · Referee, Ann are attached'],
	['sent, before any poll: the send names who was attached', at({ sent: posted([ann]), sentAt: SENT_AT }), 'sent · Ann is attached'],
	['sent, a poll said nobody: it outranks the send', at({ attached: [], sent: posted([ann]), sentAt: SENT_AT }), 'sent · it waits in the inbox'],
	['sent, nobody, launch-able', at({ agent: claude(), attached: [], sent: posted(), sentAt: SENT_AT }), 'sent · Claude will start'],
	['sent, nobody, no launching', at({ attached: [], sent: posted(), sentAt: SENT_AT }), 'sent · it waits in the inbox'],
	// the agent's done turn leaves it on the attachment list; it is not listening
	['sent, the done agent is not attached', at({ agent: claude({ state: 'done', started: BEFORE }), attached: [{ who: 'Claude', kind: 'agent' }], sent: posted(), sentAt: SENT_AT }), 'sent · Claude will start'],
	['failed at rest', at({ agent: claude({ state: 'failed', error: 'exit 2', started: BEFORE }), attached: [referee] }), 'Claude could not run: exit 2'],
	['failed at rest, no error given', at({ agent: claude({ state: 'failed' }) }), 'Claude could not run: it stopped with an error'],
	['stopped at rest', at({ agent: claude({ state: 'stopped' }), attached: [referee] }), 'Claude was stopped'],
	['listening', at({ agent: claude({ launch: false }), attached: [referee] }), 'Referee is attached'],
	['listening, the done agent left out', at({ agent: claude({ state: 'done' }), attached: [{ who: 'Claude', kind: 'agent' }, referee] }), 'Referee is attached'],
	// a running agent of the same name would be listed; only a done one is dropped
	['listening, an agent not done is kept', at({ agent: claude({ launch: false }), attached: [{ who: 'Claude', kind: 'agent' }] }), 'Claude is attached'],
	['launch-able agent', at({ agent: claude(), attached: [] }), 'Claude starts when you send'],
	['launch-able, unnamed', at({ agent: claude({ name: '' }), attached: [] }), 'nobody is attached — messages wait in the inbox'],
	['nobody', at({ agent: claude({ launch: false }), attached: [] }), 'nobody is attached — messages wait in the inbox'],
	['no publisher answer yet', at({}), 'nobody is attached — messages wait in the inbox']
];

describe('the Chat status line', () => {
	it.each(rows)('%s', (_, input, line) => {
		expect(statusLine(input)).toBe(line);
	});
});
