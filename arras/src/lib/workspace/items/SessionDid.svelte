<script lang="ts">
	// What it did (plan 0.14): the plain record of everything done through loom in a session — its `run.log`, in order, newest at the bottom and the first thing seen. A row that made or changed an annotation links it, names what it is on by the key it was filed under — `sh-0009`, `drafting/main.tex`, never `Theorem 3.1`, which a renumbering changes — and says where it stands. Nothing here is inferred: a row is a line the log holds (P3).
	import { onMount, tick } from 'svelte';
	import type { Annotation } from '$lib/manifest/types';
	import { store } from '$lib/manifest/client.svelte';
	import { when } from '$lib/sessions/when';
	import type { Item } from '../item';
	import { recordOf } from './session';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const log = $derived(recordOf(m, item.id).log ?? []);

	/** The first row that names each annotation: the one that made it, and the one a mark travels back to. */
	const first = $derived.by(() => {
		const seen = new Set<string>();
		return log.map((e) => {
			if (!e.annotation || seen.has(e.annotation)) return false;
			seen.add(e.annotation);
			return true;
		});
	});

	/** What an annotation is on, by the key it was filed under; a note on a work's page by the work and the page. */
	function fixed(a: Annotation): string {
		if (a.target.page != null) {
			const work = Object.values(m.references).find((r) => r.work === a.target.key || r.works?.includes(a.target.key));
			return `${work?.citekey ?? a.target.key} p.${a.target.page}`;
		}
		return a.target.key;
	}

	function standing(a: Annotation): string {
		return a.discarded ? 'discarded' : a.status;
	}

	function clock(stamp: string): string {
		const d = new Date(stamp);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
	}

	let scroller: HTMLElement | undefined = $state();
	// The newest action is the first thing seen.
	onMount(async () => {
		await tick();
		if (scroller) scroller.scrollTop = scroller.scrollHeight;
	});
</script>

<div class="did" bind:this={scroller} data-testid="session-did">
	{#if log.length}
		<ol class="rows">
			{#each log as e, i (i)}
				{@const a = e.annotation ? m.annotations[e.annotation] : undefined}
				<li class="row" id={a && first[i] ? `ann-${a.id}` : undefined} data-testid="did-row">
					<span class="when" title={e.time}>{when(e.time)} {clock(e.time)}</span>
					<code class="command">{e.command}</code>
					{#if a}
						<span class="made">
							<a href="quilt:{a.id}" title={a.id} data-testid="did-annotation">{a.in_reply_to ? 'reply' : a.kind}</a>
							<span class="on">{fixed(a)}</span>
							<span class="state state-{standing(a)}" data-testid="did-state">{standing(a)}</span>
						</span>
					{/if}
				</li>
			{/each}
		</ol>
	{:else}
		<p class="empty muted">Nothing done through loom in this session yet.</p>
	{/if}
</div>

<style>
	.did {
		height: 100%;
		min-height: 0;
		overflow: auto;
		padding: var(--gap) var(--gap-wide);
		font-family: var(--sans);
		font-size: 12px;
	}
	.rows {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.row {
		display: grid;
		grid-template-columns: 8.5rem minmax(0, 1fr);
		column-gap: var(--gap);
		padding: 3px 0;
		border-bottom: 1px solid var(--rule-faint, var(--rule));
	}
	.when {
		color: var(--ink-faint);
		font-size: 11px;
		padding-top: 1px;
	}
	.command {
		background: none;
		padding: 0;
		font-family: var(--mono, ui-monospace, monospace);
		font-size: 11.5px;
		color: var(--ink-soft);
		overflow-wrap: anywhere;
	}
	.made {
		grid-column: 2;
		display: flex;
		gap: 8px;
		align-items: baseline;
	}
	.on {
		font-family: var(--mono, ui-monospace, monospace);
		font-size: 11px;
		color: var(--ink-soft);
	}
	.state {
		font-size: 11px;
		color: var(--ink-faint);
	}
	.state-open {
		color: var(--ink-soft);
	}
	.empty {
		margin: 0;
	}
</style>
