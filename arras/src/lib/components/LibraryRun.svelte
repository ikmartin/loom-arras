<script lang="ts">
	// A button that starts a library run over `works` (none is every work), from scratch with `redo`. Where the run may want the network and the quilt has it off, it asks first (`NetworkAsk`): under the button, or wherever `onask` puts the question when the button stands in a row of others.
	import { store } from '$lib/manifest/client.svelte';
	import { jobs, running } from '$lib/jobs.svelte';
	import NetworkAsk from './NetworkAsk.svelte';

	let {
		works,
		label,
		network = true,
		test,
		look = 'link',
		redo = false,
		onask
	}: { works: string[]; label: string; network?: boolean; test: string; look?: 'link' | 'button'; redo?: boolean; onask?: (go: (allow: boolean | null) => void) => void } = $props();

	let asking = $state(false);
	let refused = $state('');
	const online = $derived(store.manifest?.config?.library.online === true);
	// one work is busy under any run acting on it; a run over several, or every work, is followed by its own set
	const job = $derived(works.length === 1 ? jobs.forWork(works[0]) : jobs.forWorks(works));
	const busy = $derived(running(job));

	/** Run, with the network or without; `null` is the question answered with Cancel. */
	async function go(allow: boolean | null): Promise<void> {
		asking = false;
		refused = '';
		if (allow === null) return;
		const answer = await jobs.start(works, { online: allow, redo });
		if (!answer.ok) refused = answer.error?.message ?? 'The run could not start';
	}
	function press(): void {
		if (!network || online) void go(false);
		else if (onask) onask((allow) => void go(allow));
		else asking = true;
	}
</script>

<span class="wrap">
	<button class="act" class:button={look === 'button'} disabled={busy} onclick={press} data-testid={test}>{busy ? 'running…' : label}</button>
	{#if asking}<NetworkAsk onallow={() => void go(true)} onoffline={() => void go(false)} oncancel={() => void go(null)} />{/if}
	{#if refused}<span class="refused" role="alert">{refused}</span>{/if}
</span>

<style>
	.wrap {
		display: contents;
	}
	.act {
		border: 0;
		background: none;
		color: var(--link);
		padding: 0;
		font: inherit;
		cursor: pointer;
	}
	.act:hover:not(:disabled) {
		text-decoration: underline;
	}
	.act:disabled {
		color: var(--ink-faint);
		cursor: default;
	}
	.act.button {
		font-size: 12.5px;
		padding: 4px 12px;
		border: 1px solid var(--rule);
		border-radius: 8px;
		background: var(--sheet);
		color: var(--ink);
	}
	.act.button:hover:not(:disabled) {
		text-decoration: none;
		background: var(--link-wash);
	}
	.refused {
		flex-basis: 100%;
		color: var(--state-conflicted);
		font-size: 12px;
	}
</style>
