<script lang="ts">
	// A session's transcript (plan 0.20.1): what agents said into the session with `loom session say`, newest at the bottom and the first thing seen, read beside the documents it discusses. The viewer posts nothing into it: a conversation with an agent happens in the agent's own app. Annotations are not here — a message says what it carried, and an agent links what it wrote (V2).
	//
	// **Flat, like a log.** A line saying who and when, then the words at full width; the agent's messages carry a faint rule and nothing else tells the two parties apart (V6).
	//
	// **A long report folds after its first block.** A mode's report is one message whose blocks the publisher marks (`fold.ts`): its first block and a control show, and the rest is mounted only when opened, so a 40 KB report costs nothing to typeset until it is read, and the reader lands on its summary rather than its end. Which are open is this view's alone and remembered nowhere.
	//
	// **One transcript at a time.** The transcript on screen is the selected session's: arriving here by a link or a URL selects it and closes any other session, so the footer and the transcript never name two different sessions.
	import { onDestroy, tick, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import { split } from '$lib/sessions/fold';
	import { sessionView } from '$lib/sessions/sessions.svelte';
	import { carried, isAgent, Transcript } from '$lib/sessions/transcript.svelte';
	import { when } from '$lib/sessions/when';
	import { capabilities } from '$lib/write';
	import type { Item } from '../item';
	import { soleSession } from '../links';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const row = $derived((m.sessions ?? []).find((s) => s.id === item.id));
	const seq = $derived(row?.seq ?? 0);

	const log = new Transcript(untrack(() => item.id));
	/** Whether a publisher is serving, and so answering `/_api/events`: what lets the transcript follow new messages as they land. */
	let live = $state(false);
	/** A publisher that serves the write API serves its events read beside it. */
	const serving = async (): Promise<boolean> => (await capabilities()) !== null;
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

	// A reader at the newest stays there when the log's own height changes -- a message's formulas typesetting, the window narrowing -- which otherwise keeps the offset and drops the newest below the fold (V1).
	let pinned = true;
	$effect(() => {
		const s = scroller;
		if (!s) return;
		// Where the reader is decides, on every scroll but one that ends where the re-pinning below sent it: content that grows over several frames would otherwise read that scroll as the reader leaving, and a reader's scroll that arrives in the same event is still theirs.
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
	/** Set once the newest page is in: a poll before it would ask for everything since nothing, which is the whole transcript. Polling starts on it. */
	let landed = $state(false);
	async function land(): Promise<void> {
		const served = (await serving()) ? await log.latest() : null;
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
		if (log.last !== before && stay) await toBottom();
	}
	$effect(() => {
		void serving().then((ok) => (live = ok));
	});
	$effect(() => {
		if (!live || !landed) return;
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

	/** The messages whose folded blocks are open, by seq. */
	let opened: Record<number, boolean> = $state({});
	function toggle(at: number): void {
		// opening unpins the reader, so a reader at the newest message is not carried to the end of the report they opened
		if (!opened[at]) pinned = false;
		opened = { ...opened, [at]: !opened[at] };
	}

	function clock(stamp: string): string {
		const d = new Date(stamp);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
	}
</script>

<div class="chat" data-testid="chat">
	<div class="log" bind:this={scroller} data-testid="chat-log">
		<div class="top" bind:this={top} aria-hidden="true"></div>
		<ol class="messages" data-testid="transcript">
			{#each log.events as e (e.seq)}
				<li class="message" class:agent={isAgent(e.who)} data-testid="message-{e.seq}">
					<p class="meta"><span class="who">{e.who}</span> · <span class="when" title={e.when}>{when(e.when)} {clock(e.when)}</span></p>
					{#if e.body_html}
						{@const f = split(e.body_html)}
						{#if f}
							<Prose html={f.head} />
							<button type="button" class="fold" aria-expanded={!!opened[e.seq]} data-testid="message-fold" onclick={() => toggle(e.seq)}>{opened[e.seq] ? '▾' : '▸'} {f.names.length} more: {f.names.join(', ')}</button>
							{#if opened[e.seq]}<div data-testid="message-folded"><Prose html={f.rest} /></div>{/if}
						{:else}
							<Prose html={e.body_html} />
						{/if}
					{/if}
					{#if e.changed?.length}<p class="carried" data-testid="message-carried">{carried(e.changed)}</p>{/if}
				</li>
			{:else}
				{#if !log.loading}<li class="empty muted">Nothing has been said in this session yet.</li>{/if}
			{/each}
		</ol>
	</div>
</div>

<style>
	/* The transcript takes the pane's whole width, its margin growing a little with the pane. Not `--measure`, which is the paper's text block (33rem in the paper formats) and leaves a wide pane mostly blank. */
	.chat {
		--chat-margin: clamp(var(--gap-wide), 4%, 3rem);
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}
	.log {
		flex: 1 1 auto;
		min-height: 0;
		overflow: auto;
		padding: var(--gap) var(--chat-margin);
	}
	.top {
		height: 1px;
	}
	.messages {
		list-style: none;
		margin-block: 0;
		padding: 0;
	}
	.message + .message {
		margin-top: var(--gap);
	}
	/* both voices stand at one edge: the agent's carries a rule, the person's the same inset with none */
	.message {
		border-left: 2px solid transparent;
		padding-left: var(--gap-tight);
	}
	.message.agent {
		border-left-color: var(--rule);
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
	.fold {
		display: block;
		margin: var(--gap-hair) 0;
		padding: 0;
		border: 0;
		background: none;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
		cursor: pointer;
	}
	.fold:hover {
		color: var(--ink-soft);
	}
	.carried {
		margin: 2px 0 0;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink-faint);
	}
</style>
