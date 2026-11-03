<script lang="ts">
	// Changes (plan 0.22.8, 0.25.1): what changed in the open files since the reviewer's look, each file with its diff, kept or undone whole or one change at a time. Keeping takes the text into the look; undoing puts the text at the look back, after asking, and loom keeps the text it replaces in the history first; undoing a file new since the look removes it. Who made a change is not said, since loom cannot know it. Both verbs are the author's, and say nothing about whether the mathematics is right, which is what Needs review is for. Each answer is said beside the control that made it: in the file's row while the file is still listed, else in the bar.
	import DiffView from '$lib/components/DiffView.svelte';
	import ActionBar from '$lib/review/ActionBar.svelte';
	import Empty from '$lib/review/Empty.svelte';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';
	import Said from '$lib/review/Said.svelte';
	import { fileHref } from '$lib/shell/files';
	import { store } from '$lib/manifest/client.svelte';
	import type { FileChange } from '$lib/manifest/types';
	import { can, write } from '$lib/write';
	import { onMount } from 'svelte';

	type Verb = 'changes-keep' | 'changes-undo';

	const m = $derived(store.manifest!);
	const changes = $derived(m.changes ?? []);
	const since = $derived(m.changes_since);
	const when = $derived(since ? since.when.slice(0, 16).replace('T', ' ') : '');
	let acts = $state(false);
	// what is running, by the place it was asked from: '*' for the page, a path, or `path#n` for one change
	let busy = $state<{ at: string; verb: Verb } | null>(null);
	let asking = $state('');
	let said = $state<{ at: string; text: string; refused: boolean } | null>(null);
	onMount(() => {
		void can('changes-keep').then((yes) => (acts = yes));
	});

	const WHAT: Record<string, string> = { changed: 'changed', new: 'new since your look', gone: 'gone since your look' };
	const files = (n: number) => `${n} ${n === 1 ? 'file' : 'files'}`;
	const capital = (t: string) => t.charAt(0).toUpperCase() + t.slice(1) + (t.endsWith('.') ? '' : '.');

	function href(c: FileChange): string | null {
		const f = (m.files ?? []).find((x) => x.path === c.path);
		return c.kind !== 'gone' && f ? fileHref(m, f) : null;
	}
	function label(at: string, verb: Verb, idle: string): string {
		return busy?.at === at && busy.verb === verb ? (verb === 'changes-keep' ? 'Keeping…' : 'Undoing…') : idle;
	}

	/** Keep or undo the whole page, one file, or one change, against the file as this page drew it; the buttons stay busy until the page has been drawn again, so a row that is going is never left live. */
	async function act(verb: Verb, c?: FileChange, hunk?: number): Promise<void> {
		const at = !c ? '*' : hunk === undefined ? c.path : `${c.path}#${hunk}`;
		busy = { at, verb };
		asking = '';
		said = null;
		const body: Record<string, unknown> = {};
		if (c) {
			body.path = c.path;
			if (c.hash) body.seen = c.hash;
			if (hunk !== undefined) body.hunk = hunk;
		}
		const done = await write(verb, body);
		if (done.ok || done.error?.code === 'stale') await store.refresh();
		const stale = done.error?.code === 'stale';
		const text = done.ok ? capital(done.result ?? 'done') : stale ? 'This file changed since the page was drawn; it is drawn again now.' : (done.error?.message ?? 'The publisher refused it.');
		const still = !!c && (store.manifest?.changes ?? []).some((x) => x.path === c.path);
		said = { at: still ? c!.path : '*', text, refused: !done.ok };
		busy = null;
	}
</script>

<main class="page scrollbar-shown" data-testid="changes">
	<ReviewHeading title="Changes" />
	{#if !since}
		<Empty text="Nothing to compare against yet: the publisher takes your first look at the open files when it starts." testid="changes-none" />
	{:else}
		<ActionBar testid="changes-bar" said={said?.at === '*' ? said.text : ''} refused={said?.refused}>
			{#snippet lead()}
				{#if changes.length}<b>{files(changes.length)}</b> changed since your look, {when}{:else}Nothing has changed since your look, {when}{/if}
			{/snippet}
			{#snippet actions()}
				{#if acts && changes.length}<button class="btn" onclick={() => act('changes-keep')} disabled={!!busy} data-testid="changes-keep-all">{label('*', 'changes-keep', 'Keep all')}</button>{/if}
			{/snippet}
		</ActionBar>
		<p class="lead">Keep a change to take it into your look; undo one to put it back as it was at your look, its text now kept. Neither says whether the mathematics is right.</p>
		{#if !changes.length}
			<Empty text="Nothing has changed since your look." testid="changes-empty" />
		{/if}
		{#each changes as c (c.path)}
			{@const open = href(c)}
			{@const several = (c.hunks ?? 0) > 1}
			<section class="change" data-testid="change" data-path={c.path}>
				<header class="head">
					<h2>
						{#if open}<a href={open} data-testid="change-open">{c.path}</a>{:else}<code>{c.path}</code>{/if}
						<span class="muted">{WHAT[c.kind] ?? c.kind}{several ? ` · ${c.hunks} changes` : ''}</span>
					</h2>
					{#if acts}
						<span class="acts">
							{#if asking === c.path}
								<span class="ask" data-testid="undo-ask">{c.kind === 'new' ? `Remove ${c.path}? Its text is kept.` : `Put ${c.path} back as it was at your look? Its text now is kept.`}</span>
								<button class="btn small primary" onclick={() => act('changes-undo', c)} disabled={!!busy} data-testid="undo-go">{c.kind === 'new' ? 'Remove' : 'Undo'}</button>
								<button class="btn small quiet" onclick={() => (asking = '')} data-testid="undo-cancel">Cancel</button>
							{:else}
								<button class="btn small" onclick={() => act('changes-keep', c)} disabled={!!busy} data-testid="change-keep">{label(c.path, 'changes-keep', several ? 'Keep all of it' : 'Keep')}</button>
								<button class="btn small" onclick={() => (asking = c.path)} disabled={!!busy} data-testid="change-undo">{label(c.path, 'changes-undo', c.kind === 'new' ? 'Remove…' : several ? 'Undo all of it…' : 'Undo…')}</button>
							{/if}
						</span>
					{/if}
				</header>
				{#if said?.at === c.path}<Said text={said.text} refused={said.refused} testid="change-said" />{/if}
				{#snippet hunk(n: number)}
					{@const at = `${c.path}#${n}`}
					{#if asking === at}
						<span data-testid="hunk-ask">Put this change back? Its text now is kept.</span>
						<button class="btn small primary" onclick={() => act('changes-undo', c, n)} disabled={!!busy} data-testid="hunk-undo-go">Undo</button>
						<button class="btn small quiet" onclick={() => (asking = '')}>Cancel</button>
					{:else}
						<button class="btn small" onclick={() => act('changes-keep', c, n)} disabled={!!busy} data-testid="hunk-keep">{label(at, 'changes-keep', 'Keep')}</button>
						<button class="btn small" onclick={() => (asking = at)} disabled={!!busy} data-testid="hunk-undo">{label(at, 'changes-undo', 'Undo…')}</button>
					{/if}
				{/snippet}
				{#if c.diff}<DiffView path={c.diff} hunk={acts && several ? hunk : undefined} />{/if}
			</section>
		{/each}
	{/if}
</main>

<style>
	.change {
		margin: var(--gap-wide) 0;
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--gap-tight);
		margin-bottom: var(--gap-hair);
	}
	.head h2 {
		margin: 0;
		font-size: 13px;
		font-weight: 600;
		text-transform: none;
		letter-spacing: 0;
		overflow-wrap: anywhere;
	}
	.head h2 a,
	.head h2 code {
		font-family: var(--mono);
		font-size: 12.5px;
	}
	.acts {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--gap-tight);
	}
	.ask {
		font-size: 12.5px;
		color: var(--ink);
	}
</style>
