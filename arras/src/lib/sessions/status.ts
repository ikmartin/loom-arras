// The Chat's status line: one line on who is listening, read off what the publisher last said and what the last send came back with.

import type { AgentState, Listener, Posted } from './transcript.svelte';

/** What the status line reads: the publisher's agent and listeners from the last poll, and the last send with the second it went. */
export interface StatusInput {
	/** The agent the publisher starts, or null where no publisher answers. */
	agent: AgentState | null;
	/** Who the publisher says is listening, or null before any poll answered. */
	attached: Listener[] | null;
	/** What the last send came back with, until someone answers it. */
	sent: Posted | null;
	/** When that send went, as a whole-second ISO stamp; '' before any send. */
	sentAt: string;
}

/** One line, never empty, on who is listening: the turn loom started, where it starts one; else who is attached; and after a send, what became of it. It claims only what the publisher knows — the process's state and the last command it ran (P3). */
export function statusLine({ agent, attached, sent, sentAt }: StatusInput): string {
	if (agent?.blocked) return `${agent.name || 'The agent'} cannot be started: ${agent.blocked}`;
	if (agent?.state === 'running') return `${agent.name} is working` + (agent.activity ? ` · ${agent.activity}` : '');
	// a turn that began after the send answers what became of it, and outranks "will start"
	const since = !!(sent && agent?.started && agent.started >= sentAt);
	if (since && agent?.state === 'failed') return `${agent.name} could not run: ${agent.error || 'it stopped with an error'}`;
	if (since && agent?.state === 'stopped') return `${agent.name} was stopped`;
	// an agent whose turn is done is no longer listening, whatever the attachment list still says
	const rows = (attached ?? sent?.attached ?? []).filter((r) => r.who !== agent?.name || agent?.state !== 'done');
	const listening = rows.length ? `${rows.map((r) => r.who).join(', ')} ${rows.length === 1 ? 'is' : 'are'} attached` : '';
	if (sent) return listening ? `sent · ${listening}` : agent?.launch ? `sent · ${agent.name} will start` : 'sent · it waits in the inbox';
	if (agent?.state === 'failed') return `${agent.name} could not run: ${agent.error || 'it stopped with an error'}`;
	if (agent?.state === 'stopped') return `${agent.name} was stopped`;
	if (listening) return listening;
	return agent?.launch && agent.name ? `${agent.name} starts when you send` : 'nobody is attached — messages wait in the inbox';
}
