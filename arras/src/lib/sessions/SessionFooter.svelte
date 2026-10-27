<script lang="ts">
	// The column's footer (plan 0.13.3 S5–S8): where annotations will be written, pinned outside the column's scroll so a reader never goes looking for it. It carries only the state — a dot, the session's name, whose annotations the page shows in a word, what is new — and opens the picker, where that scope is chosen; the sentence explaining a refusal stands beside the refused control, not here. Folded (`compact`), it is the dot alone.
	//
	// Its tone is `writable()`'s answer, which concerns annotations only: review decisions and incorporating a pull name no session, so an amber footer never means nothing can be written.
	import Popover from '$lib/components/Popover.svelte';
	import DeleteSession from './DeleteSession.svelte';
	import SessionPicker from './SessionPicker.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { selected, sessionView, summary, titleOf, writable } from './sessions.svelte';
	import { write } from '$lib/write';
	import type { SessionRow } from '$lib/manifest/types';

	let { compact = false }: { compact?: boolean } = $props();

	const m = $derived(store.manifest);
	const here = $derived(selected(m));
	const why = $derived(writable(m));
	const fresh = $derived(here ? summary(m, here.id).fresh : 0);
	const name = $derived(here ? titleOf(here) : 'no session selected');
	// seeing one session's annotations only is a state that should not be hidden behind the picker
	const scope = $derived(sessionView.view === 'current' ? 'this session' : 'all');

	let open = $state(false);
	// The confirmation stands outside the picker: a press inside a dialog is a press outside the picker, which would close it and take the dialog with it.
	let doomed = $state<SessionRow | null>(null);

	async function remove(s: SessionRow): Promise<void> {
		doomed = null;
		const res = await write('session-delete', { session: s.id });
		store.refresh();
		if (res.ok) sessionView.dropped(s.id);
	}

	// A pending rename is dropped once the manifest carries it.
	$effect(() => {
		for (const [id, t] of Object.entries(sessionView.renamed)) {
			if ((m?.sessions ?? []).find((s) => s.id === id)?.title === t) delete sessionView.renamed[id];
		}
	});
</script>

<div class="footer" class:refused={!!why} class:compact>
	<Popover bind:open placement="above" width={320} block label="Sessions">
		{#snippet trigger({ open, toggle })}
			<button
				type="button"
				class="state"
				aria-haspopup="dialog"
				aria-expanded={open}
				aria-label={why ? `annotations cannot be written: ${why}` : `annotations are written into ${name}`}
				title={compact ? `${name} · showing ${scope}` : undefined}
				data-testid="session-footer"
				onclick={toggle}
			>
				<span class="dot" aria-hidden="true"></span>
				{#if !compact}
					<span class="name" data-testid="session-footer-name">{name}</span>
					<span class="scope" title="showing annotations from {scope === 'all' ? 'every session' : 'this session only'}" data-testid="session-footer-scope">· {scope}</span>
					{#if fresh}<span class="fresh" title="{fresh} new since you last opened it">{fresh}</span>{/if}
					<span class="chev" aria-hidden="true"></span>
				{/if}
			</button>
		{/snippet}
		<SessionPicker
			onpicked={() => (open = false)}
			ondelete={(s) => {
				open = false;
				doomed = s;
			}}
		/>
	</Popover>
</div>

{#if doomed}
	<DeleteSession title={titleOf(doomed)} open={summary(m, doomed.id).open} onCancel={() => (doomed = null)} onDelete={() => remove(doomed!)} />
{/if}

<style>
	.footer {
		flex: none;
		margin: 0 -14px calc(-1 * var(--gap));
		border-top: 1px solid var(--rule);
	}
	.state {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		font-family: var(--sans);
		font-size: 12px;
		color: var(--ink);
		background: none;
		border: 0;
		padding: 10px 14px;
		text-align: left;
		cursor: pointer;
	}
	.state:hover {
		background: var(--sheet);
	}
	.dot {
		flex: none;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--link);
	}
	.name {
		flex: 1 1 auto;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.scope {
		flex: none;
		color: var(--ink-faint);
	}
	.compact .state {
		justify-content: center;
		padding: 10px 0;
	}
	.fresh {
		flex: none;
		font-size: 11px;
		font-variant-numeric: tabular-nums;
		padding: 0 6px;
		border-radius: var(--rad-pill);
		background: var(--mark);
		color: var(--state-stale);
	}
	.chev {
		flex: none;
		width: 5px;
		height: 5px;
		border-right: 1.5px solid var(--ink-faint);
		border-bottom: 1.5px solid var(--ink-faint);
		transform: rotate(-45deg);
	}
	/* Refused (S6): amber fill, a hollow ring, the name in warning ink. The state only; the sentence is beside the refused control. */
	.refused {
		background: var(--state-stale-wash);
	}
	.refused .state:hover {
		background: none;
	}
	.refused .dot {
		background: none;
		box-shadow: inset 0 0 0 1.5px var(--state-stale);
	}
	.refused .name {
		color: var(--state-stale);
	}
</style>
