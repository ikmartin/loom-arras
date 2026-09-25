<script lang="ts">
	// What the next message will carry (plan 0.14): the annotations the person wrote in this session since a message last carried any. Drawn only while it holds something; each row is a dot in the kind's hue (15.3.9; annotation study A2) and a link to the annotation, followed by the one rule so the Chat stays; the preview is the text the agent will read, verbatim, since it is the publisher's own rendering of what it will send.
	import { base } from '$app/paths';
	import { store } from '$lib/manifest/client.svelte';
	import { keyName } from '$lib/workspace/names';
	import type { PacketRow } from './transcript.svelte';

	let { session, refresh = 0, oncount }: { session: string; refresh?: number; oncount?: (n: number) => void } = $props();

	let rows = $state<PacketRow[]>([]);
	let text = $state('');
	let preview = $state(false);

	// Asked again when the manifest moves — a write rebuilds it — and after each send.
	$effect(() => {
		const id = session;
		void store.hash;
		void refresh;
		let dropped = false;
		fetch(`${base}/_api/packet?session=${encodeURIComponent(id)}`)
			.then((r) => (r.ok ? r.json() : null))
			.then((j) => {
				if (dropped || !j) return;
				rows = Array.isArray(j.rows) ? j.rows : [];
				text = typeof j.text === 'string' ? j.text : '';
				oncount?.(rows.length);
			})
			.catch(() => {});
		return () => {
			dropped = true;
		};
	});

	const m = $derived(store.manifest);
	function name(r: PacketRow): string {
		if (r.work) return r.page ? `${r.work} p. ${r.page}` : r.work;
		return m ? keyName(m, r.target) : r.target;
	}
	/** What the dot says for a screen reader: the kind, and that a reply is one. */
	function kindOf(r: PacketRow): string {
		return r.act === 'replied' ? `reply, ${r.kind}` : r.kind;
	}
</script>

{#if rows.length}
	<div class="tray" data-testid="packet-tray">
		<p class="head">
			<span>goes with your next message</span>
			<button type="button" class="as-link" aria-expanded={preview} data-testid="packet-preview-toggle" onclick={() => (preview = !preview)}>{preview ? 'hide preview' : 'preview'}</button>
		</p>
		<ul>
			{#each rows as r (r.id)}
				<li data-testid="packet-row-{r.id}">
					<span class="ann-dot k-{r.kind}" class:reply={r.act === 'replied'} role="img" aria-label={kindOf(r)} title={kindOf(r)} data-testid="packet-kind"></span>
					<a href="quilt:{r.id}" title={r.target}>{name(r)}</a>
				</li>
			{/each}
		</ul>
		{#if preview}<pre data-testid="packet-preview">{text}</pre>{/if}
	</div>
{/if}

<style>
	.tray {
		border-top: 1px solid var(--rule);
		padding: 4px var(--gap-wide) 6px;
		font-family: var(--sans);
		font-size: 11.5px;
		/* its own height, up to the cap: shrinking with the log, it showed one line of the preview under a long transcript */
		flex: none;
		max-height: 40%;
		overflow: auto;
	}
	.head {
		display: flex;
		justify-content: space-between;
		margin: 0 0 2px;
		color: var(--ink-faint);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: flex;
		gap: 6px;
		align-items: center;
		padding: 1px 0;
	}
	pre {
		margin: 4px 0 0;
		padding: 6px;
		background: var(--leaf);
		border-radius: var(--rad-control, 3px);
		font-size: 11px;
		white-space: pre-wrap;
	}
</style>
