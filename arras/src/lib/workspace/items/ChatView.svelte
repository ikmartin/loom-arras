<script lang="ts">
	// A session's Chat (plan 0.14): the conversation and its input in one pane. The transcript is every message the person and the agent said, newest at the bottom and the first thing seen; beneath it one line on who is listening, and the input. Annotations are not here — a message says what it carried, and an agent links what it wrote (P2).
	//
	// **Flat, like a log.** A line saying who and when, then the words at full width; the agent's messages carry a faint rule and nothing else tells the two parties apart (P6).
	//
	// **One Chat at a time.** The Chat on screen is the selected session's: arriving here by a link or a URL selects it and closes any other session, so the footer and the Chat never name two different conversations.
	import { onDestroy, tick, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import Composer from '$lib/sessions/Composer.svelte';
	import PacketTray from '$lib/sessions/PacketTray.svelte';
	import { sessionView } from '$lib/sessions/sessions.svelte';
	import { carried, isAgent, Transcript, type Listener, type Posted } from '$lib/sessions/transcript.svelte';
	import { when } from '$lib/sessions/when';
	import { can, write } from '$lib/write';
	import type { Item } from '../item';
	import { soleSession } from '../links';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const row = $derived((m.sessions ?? []).find((s) => s.id === item.id));
	const seq = $derived(row?.seq ?? 0);

	const log = new Transcript(untrack(() => item.id));
	/** Whether a publisher is serving, which is what makes the status line and the input honest (P3). */
	let live = $state(false);
	/** How many annotations the next message will carry, and a nudge that asks the tray again after a send. */
	let packed = $state(0);
	let sends = $state(0);
	/** What the last send came back with, until someone answers it, and when it went. */
	let sent = $state<Posted | null>(null);
	let sentAt = '';
	let scroller: HTMLElement | undefined = $state();
	let top: HTMLElement | undefined = $state();

	$effect(() => {
		const id = item.id;
		untrack(() => {
			if (sessionView.selected !== id) sessionView.select(id, store.manifest);
			soleSession(id);
		});
	});

	/** Whether the reader is at the newest message, so a new one keeps them there and does not pull them down from further up. */
	function atBottom(): boolean {
		const s = scroller;
		return !s || s.scrollHeight - s.scrollTop - s.clientHeight < 24;
	}

	async function toBottom(): Promise<void> {
		await tick();
		if (!scroller) return;
		pinned = true;
		scroller.scrollTop = scroller.scrollHeight;
	}

	// A reader at the newest stays there when the log's own height changes -- the tray opening, the input growing, the window narrowing -- which otherwise keeps the offset and drops the newest below the fold (P1).
	let pinned = true;
	$effect(() => {
		const s = scroller;
		if (!s) return;
		// Where the reader is decides, on every scroll but one that ends where the re-pinning below sent it: a tray that grows over several frames would otherwise read that scroll as the reader leaving, and a reader's scroll that arrives in the same event is still theirs.
		let ours: number | null = null;
		const onscroll = () => {
			if (ours === null || Math.abs(s.scrollTop - ours) > 1) pinned = atBottom();
			ours = null;
		};
		s.addEventListener('scroll', onscroll, { passive: true });
		const seen = new ResizeObserver(() => {
			const bottom = s.scrollHeight - s.clientHeight;
			if (!pinned || Math.abs(s.scrollTop - bottom) <= 1) return;
			ours = bottom;
			s.scrollTop = bottom;
		});
		seen.observe(s);
		return () => {
			s.removeEventListener('scroll', onscroll);
			seen.disconnect();
		};
	});

	// The newest page first: from the publisher where one serves, whose count is current, else from the manifest.
	/** Set once the newest page is in: a poll before it would ask for everything since nothing, which is the whole transcript. */
	let landed = false;
	async function land(): Promise<void> {
		const served = (await can('message')) ? await log.latest() : null;
		await log.load(served ?? untrack(() => seq));
		landed = true;
		await toBottom();
	}
	void land();

	// The manifest's own count moves in a static build and under a publisher alike; in a static one it is the only signal.
	$effect(() => {
		const upto = seq;
		// before landing, `live` is not yet known: the manifest's count would load its own page beside the publisher's
		if (landed && upto > untrack(() => log.last) && !live) {
			const stay = atBottom();
			void log.load(upto).then(() => (stay ? toBottom() : undefined));
		}
	});

	let timer: ReturnType<typeof setInterval> | undefined;
	async function poll(): Promise<void> {
		if (!landed || document.visibilityState === 'hidden') return;
		const stay = atBottom();
		const before = log.last;
		await log.poll();
		if (sent?.seq && log.last > sent.seq) sent = null;
		if (log.last !== before && stay) await toBottom();
	}
	$effect(() => {
		void can('message').then((ok) => (live = ok));
	});
	$effect(() => {
		if (!live) return;
		void poll();
		timer = setInterval(() => void poll(), 1000);
		return () => clearInterval(timer);
	});
	onDestroy(() => clearInterval(timer));

	// Scrolling to the top asks for the page before, and holds the reader where they were.
	$effect(() => {
		const el = top;
		const s = scroller;
		if (!el || !s) return;
		const seen = new IntersectionObserver(async (entries) => {
			if (!entries.some((e) => e.isIntersecting) || !log.more || log.loading) return;
			const from = s.scrollHeight;
			await log.older();
			await tick();
			s.scrollTop += s.scrollHeight - from;
		}, { root: s });
		seen.observe(el);
		return () => seen.disconnect();
	});

	function names(rows: Listener[]): string {
		return rows.map((r) => r.who).join(', ');
	}

	/** One line on who is listening: the turn loom started, where it starts one; else who is attached; and after a send, what became of it. It claims only what the publisher knows — the process's state and the last command it ran (P3). */
	const status = $derived.by(() => {
		const agent = log.agent;
		if (agent?.blocked) return `${agent.name || 'The agent'} cannot be started: ${agent.blocked}`;
		if (agent?.state === 'running') return `${agent.name} is working` + (agent.activity ? ` · ${agent.activity}` : '');
		// a turn that began after the send answers what became of it, and outranks "will start"
		const since = !!(sent && agent?.started && agent.started >= sentAt);
		if (since && agent?.state === 'failed') return `${agent.name} could not run: ${agent.error || 'it stopped with an error'}`;
		if (since && agent?.state === 'stopped') return `${agent.name} was stopped`;
		const rows = (log.attached ?? sent?.attached ?? []).filter((r) => r.who !== agent?.name || agent?.state !== 'done');
		const listening = rows.length ? `${names(rows)} ${rows.length === 1 ? 'is' : 'are'} attached` : '';
		if (sent) return listening ? `sent · ${listening}` : agent?.launch ? `sent · ${agent.name} will start` : 'sent · it waits in the inbox';
		if (agent?.state === 'failed') return `${agent.name} could not run: ${agent.error || 'it stopped with an error'}`;
		if (agent?.state === 'stopped') return `${agent.name} was stopped`;
		if (listening) return listening;
		return agent?.launch && agent.name ? `${agent.name} starts when you send` : 'nobody is attached — messages wait in the inbox';
	});
	const running = $derived(log.agent?.state === 'running');

	async function stop(): Promise<void> {
		await write('agent-stop', { session: item.id });
		await log.poll();
	}

	function clock(stamp: string): string {
		const d = new Date(stamp);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
	}

	async function onsent(res: Posted): Promise<void> {
		sent = res;
		// the publisher stamps whole seconds, so the send is taken as of the start of its second
		sentAt = new Date(Math.floor(Date.now() / 1000) * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
		sends++;
		await log.poll();
		await toBottom();
	}
</script>

<div class="chat" data-testid="chat">
	<div class="log" bind:this={scroller} data-testid="chat-log">
		<div class="top" bind:this={top} aria-hidden="true"></div>
		<ol class="messages" data-testid="transcript">
			{#each log.events as e (e.seq)}
				<li class="message" class:agent={isAgent(e.who)} data-testid="message-{e.seq}">
					<p class="meta"><span class="who">{e.who}</span> · <span class="when" title={e.when}>{when(e.when)} {clock(e.when)}</span></p>
					{#if e.body_html}<Prose html={e.body_html} />{/if}
					{#if e.changed?.length}<p class="carried" data-testid="message-carried">{carried(e.changed)}</p>{/if}
				</li>
			{:else}
				{#if !log.loading}<li class="empty muted">Nothing has been said in this session yet.</li>{/if}
			{/each}
		</ol>
	</div>
	{#if live}
		<p class="status" data-testid="chat-line">
			<span role="status" data-testid="chat-status">{status}</span>
			{#if running}<button type="button" class="stop" data-testid="agent-stop" onclick={stop}>stop</button>{/if}
		</p>
		<PacketTray session={item.id} refresh={sends} oncount={(n) => (packed = n)} />
		<Composer session={item.id} {packed} {onsent} />
	{/if}
</div>

<style>
	.chat {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.log {
		flex: 1 1 auto;
		min-height: 0;
		overflow: auto;
		padding: var(--gap) var(--gap-wide);
	}
	.top {
		height: 1px;
	}
	.messages {
		list-style: none;
		margin: 0;
		padding: 0;
		max-width: var(--measure);
	}
	.message + .message {
		margin-top: var(--gap);
	}
	.message.agent {
		border-left: 2px solid var(--rule);
		padding-left: var(--gap-tight);
	}
	.meta {
		margin: 0 0 2px;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
	.who {
		color: var(--ink-soft);
	}
	.message :global(.body) {
		font-size: 0.92rem;
	}
	.message :global(.body > :first-child) {
		margin-top: 0;
	}
	.message :global(.body > :last-child) {
		margin-bottom: 0;
	}
	.empty {
		font-size: 12px;
	}
	.carried {
		margin: 2px 0 0;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
	.status {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--gap);
		margin: 0;
		padding: 4px var(--gap-wide);
		border-top: 1px solid var(--rule);
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
	.stop {
		font: inherit;
		color: var(--ink-soft);
		background: none;
		border: 1px solid var(--rule);
		border-radius: 3px;
		padding: 0 8px;
		cursor: pointer;
	}
	.stop:hover {
		color: var(--ink);
		border-color: var(--rule-strong);
	}
</style>
