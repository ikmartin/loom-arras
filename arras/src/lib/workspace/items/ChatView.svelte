<script lang="ts">
	// A session's transcript (plan 0.20.1): what agents said into the session with `loom session say`, newest at the bottom and the first thing seen, read beside the documents it discusses. The viewer posts nothing into it: a conversation with an agent happens in the agent's own app. Annotations are not here — a message says what it carried, and an agent links what it wrote (V2).
	//
	// **Flat, like a log.** A line saying who and when, then the words at full width; the agent's messages carry a faint rule and nothing else tells the two parties apart (V6).
	//
	// **A long report folds after its first block.** A mode's report is one message whose blocks the publisher marks (`fold.ts`): its first block and a control show, and the rest is mounted only when opened, so a 40 KB report costs nothing to typeset until it is read, and the reader lands on its summary rather than its end. Which are open is this view's alone and remembered nowhere.
	//
	// **Reading is not writing.** Opening a transcript, by a link, a URL or the Sessions table, chooses nothing: the footer names the session writes go to, and a transcript of another one says so at its head, with Write here. One transcript is open at a time, the one read last.
	import { onDestroy, tick, untrack } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import { split } from '$lib/sessions/fold';
	import { selected as writingIn, sessionView, titleOf } from '$lib/sessions/sessions.svelte';
	import { carried, isAgent, Transcript } from '$lib/sessions/transcript.svelte';
	import { when } from '$lib/sessions/when';
	import { capabilities } from '$lib/write';
	import type { Item } from '../item';
	import { soleSession } from '../links';
	import AnnotateChip from '$lib/fragments/AnnotateChip.svelte';
	import { notesWhere, noteWhere, quote } from '$lib/notes';
	import type { Note } from '$lib/manifest/types';

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
		untrack(() => soleSession(id));
	});
	const writing = $derived(writingIn(m));

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

	// Notes written in this session read in its discussion, by time among the messages (plan 0.22.8): a quote entered the conversation where it was taken. Faded ones are left out, as everywhere.
	const notes = $derived(notesWhere(m, (n) => n.session === item.id));
	type Entry = { kind: 'message'; e: (typeof log.events)[number] } | { kind: 'note'; n: Note };
	const entries = $derived.by<Entry[]>(() => {
		const oldest = log.more ? (log.events[0]?.when ?? '') : '';
		const out: Entry[] = log.events.map((e) => ({ kind: 'message', e }));
		for (const n of [...notes].reverse()) if (n.when >= oldest) out.push({ kind: 'note', n });
		return out.sort((a, b) => (a.kind === 'message' ? a.e.when : a.n.when).localeCompare(b.kind === 'message' ? b.e.when : b.n.when));
	});

	type Box = { left: number; top: number; width: number; height: number };
	/** Words selected in one message, offered to quote. */
	let offered = $state<{ seq: number; text: string; at: Box; range: Range } | null>(null);
	function selected(): void {
		const sel = window.getSelection();
		const words = sel?.toString().trim();
		if (!sel || !words || !sel.rangeCount) return;
		const li = (n: Node | null) => (n instanceof Element ? n : n?.parentElement)?.closest<HTMLElement>('[data-seq]');
		const a = li(sel.anchorNode);
		if (!a || a !== li(sel.focusNode)) return;
		const range = sel.getRangeAt(0);
		const r = range.getBoundingClientRect();
		offered = { seq: Number(a.dataset.seq), text: words.slice(0, 4000), at: { left: r.left, top: r.top, width: r.width, height: r.height }, range: range.cloneRange() };
	}
	let quoted = $state<Record<number, string>>({});
	async function quoteMessage(e: { seq: number; body?: string }, el: HTMLElement | null): Promise<void> {
		const words = (el?.querySelector('.body')?.textContent ?? e.body ?? '').trim().slice(0, 4000);
		const why = await quote({ target: `${item.id}#${e.seq}`, quote: words });
		quoted = { ...quoted, [e.seq]: why || 'quoted' };
		setTimeout(() => (quoted = { ...quoted, [e.seq]: '' }), why ? 2400 : 1200);
	}

	function clock(stamp: string): string {
		const d = new Date(stamp);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
	}
</script>

<div class="chat" data-testid="chat">
	{#if row && writing?.id !== item.id}
		<p class="writing" data-testid="chat-writing">
			{writing ? `You are writing in “${titleOf(writing)}”.` : 'You are not writing in a session.'}
			{#if row.state === 'open'}<button type="button" class="as-link" data-testid="chat-write-here" onclick={() => sessionView.select(item.id, m)}>Write here</button>{:else}This one is closed.{/if}
		</p>
	{/if}
	<div class="log" bind:this={scroller} data-testid="chat-log">
		<div class="top" bind:this={top} aria-hidden="true"></div>
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<ol class="messages" data-testid="transcript" onmouseup={selected}>
			{#each entries as x (x.kind === 'message' ? `m${x.e.seq}` : x.n.id)}
				{#if x.kind === 'note'}
					{@const n = x.n}
					<li class="noted" data-testid="noted-{n.id}">
						<p class="meta"><span class="who">{n.author.id}</span> quoted · <span class="when" title={n.when}>{when(n.when)} {clock(n.when)}</span> · <a href="quilt:{n.id}">{noteWhere(n)}</a></p>
						{#if n.quote}<q class="quoted">{n.quote}</q>{/if}
						{#if n.body}<p class="note-body">{n.body}</p>{/if}
					</li>
				{:else}
				{@const e = x.e}
				<li class="message" class:agent={isAgent(e.who)} data-testid="message-{e.seq}" data-seq={e.seq}>
					<p class="meta"><span class="who">{e.who}</span> · <span class="when" title={e.when}>{when(e.when)} {clock(e.when)}</span>{#if quoted[e.seq]} · <span class="faint" role="status">{quoted[e.seq]}</span>{:else} · <button type="button" class="as-link quote-message" data-testid="quote-message" onclick={(ev) => quoteMessage(e, (ev.currentTarget as HTMLElement).closest('li'))}>quote</button>{/if}</p>
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
				{/if}
			{:else}
				<li class="empty muted" data-testid="transcript-empty">{log.loading ? 'Loading the transcript…' : 'Nothing has been said in this session yet.'}</li>
			{/each}
		</ol>
	</div>
</div>
{#if offered}
	<AnnotateChip
		at={offered.at}
		range={offered.range}
		onquote={() => (offered ? quote({ target: `${item.id}#${offered.seq}`, quote: offered.text }) : Promise.resolve(''))}
		ondone={() => {
			offered = null;
			window.getSelection()?.removeAllRanges();
		}}
	/>
{/if}

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
	/* a note quoted into the session: quieter than a message, in the annotation neutral */
	.noted {
		margin-top: var(--gap);
		padding-left: var(--gap-tight);
		border-left: 2px solid var(--ann-neutral);
		color: var(--ink-soft);
	}
	.noted .quoted {
		font-style: italic;
	}
	.note-body {
		margin: var(--gap-hair) 0 0;
	}
	.quote-message {
		visibility: hidden;
	}
	.message:hover .quote-message,
	.quote-message:focus-visible {
		visibility: visible;
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
		font-size: 0.92rem;
	}
	.writing {
		flex: none;
		margin: 0;
		padding: 6px 12px;
		font-size: 12.5px;
		color: var(--ink-soft);
		border-bottom: 1px solid var(--rule);
	}
	.writing button {
		margin-left: 4px;
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
