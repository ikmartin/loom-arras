<script lang="ts">
	// A session's messages, as they land (plan 0.13 §8).
	//
	// **Fine events for appends, coarse for everything else.** A message arrives through `/_api/events`, which is a
	// small answer about one session; everything else a reader needs still comes through the manifest they already
	// poll. Rebuilding the whole manifest per message would reintroduce the re-render that closed open boxes under the
	// reader — the failure `Fragment.svelte` has been patched for twice.
	//
	// **A gap resyncs rather than stitching.** The answer carries the inbox's own last sequence number; when it is
	// further along than what arrived, some were missed, and the honest response is to ask again from where we are
	// rather than to pretend the stream was continuous.
	import { base } from '$app/paths';
	import { store } from '$lib/manifest/client.svelte';
	import { active } from './sessions.svelte';

	let { session = '' }: { session?: string } = $props();

	interface Change {
		id: string;
		kind: string;
		target: string;
		act: string;
		by: string;
		body?: string;
	}
	interface Event {
		seq: number;
		kind: string;
		who: string;
		when: string;
		body?: string;
		changed?: Change[];
	}

	const here = $derived(active(store.manifest));
	const into = $derived(session || here?.id || '');
	/** What the manifest says the inbox has reached, which is the cheap signal that there is anything to fetch. */
	const known = $derived((store.manifest?.sessions ?? []).find((s) => s.id === into)?.seq ?? 0);

	let events = $state<Event[]>([]);
	let at = $state(0);
	let gap = $state(false);

	$effect(() => {
		const id = into;
		const upto = known;
		if (!id || upto <= at) return;
		let dropped = false;
		fetch(`${base}/_api/events?session=${encodeURIComponent(id)}&since=${at}`)
			.then((r) => (r.ok ? r.json() : null))
			.then((j) => {
				if (dropped || !j) return;
				const got: Event[] = j.events ?? [];
				// the publisher's own last sequence, against what we were handed: a shortfall means we missed some
				gap = got.length > 0 && got[0].seq > at + 1;
				events = [...events, ...got];
				at = j.seq ?? at;
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	// A different session is a different conversation, not more of this one.
	$effect(() => {
		void into;
		events = [];
		at = 0;
		gap = false;
	});
</script>

{#if events.length}
	<ol class="stream" data-testid="stream">
		{#if gap}
			<li class="gap" data-testid="stream-gap">Some messages were missed; what follows is from here on.</li>
		{/if}
		{#each events as e (e.seq)}
			<li data-testid="message-{e.seq}">
				<p class="said"><span class="who">{e.who}</span> {e.body ?? ''}</p>
				{#each e.changed ?? [] as c (c.id)}
					<p class="changed" data-testid="changed-{c.id}">
						<code>{c.id}</code>
						{c.kind} · {c.target} · {c.act} by {c.by}
						<!-- the body too, because `loom session next` prints it and the decision is that both surfaces show the same post -->
						{#if c.body}<span class="said-body">{c.body}</span>{/if}
					</p>
				{/each}
			</li>
		{/each}
	</ol>
{/if}

<style>
	.stream {
		list-style: none;
		margin: 0;
		padding: 6px 12px;
		font-size: 0.84rem;
	}
	li + li {
		margin-top: 6px;
	}
	.said {
		margin: 0;
	}
	.who {
		color: var(--ink-faint, #6b6b6b);
	}
	.changed {
		margin: 2px 0 0 12px;
		font-size: 0.92em;
		color: var(--ink-faint, #6b6b6b);
	}
	.said-body {
		display: block;
		color: var(--ink, #1b1b1b);
	}
	.gap {
		color: var(--annotation, #c05621);
	}
</style>
