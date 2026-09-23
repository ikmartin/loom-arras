<script lang="ts">
	// A node (plan 0.13.3 N1–N3, phase 4): its statement and its proofs, and nothing else in the flow. The tab names it; Settings ▸ Show ids puts its id and state in the left gutter, as a document's are; its annotations are reached by their marks, which open their cards, and the rail's `show all annotations` opens every one. What the node is in, what it rests on, where its text came from, the citations suggested for it and what was discarded on it are its context, opened beside it.
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import FragmentNotes from '$lib/fragments/FragmentNotes.svelte';
	import { slotsFor } from '$lib/fragments/slots';
	import { keyUrl, nodeUrl } from '$lib/nav';
	import { fetchSource } from '$lib/source';
	import { route } from '$lib/paths';
	import type { Item } from '../item';
	import { nodeState } from '../state.svelte';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const slots = slotsFor(() => m);
	const held = $derived(nodeState(item));
	const key = $derived(item.id);
	const node = $derived(m.nodes[key]);
	const stmt = $derived(m.keys[key]);
	// A key with no node of its own — an unlabelled proof — belongs to the node that owns it, so the page points at it rather than reporting an unknown key.
	const owner = $derived(!node && stmt?.node && m.nodes[stmt.node] ? stmt.node : '');
	// by the code's own name: the publisher's namespace in front of it is the manifest's to carry, not this module's to know
	const missingProof = $derived(m.diagnostics.some((d) => d.keys.includes(key) && d.code.endsWith(':missing-proof')));
	// The source is fetched as soon as the node is shown, so the rail knows whether to offer it: a corpus that publishes none shows no control (plan 0.11 Part E).
	$effect(() => {
		const s = held;
		if (s.source === null) void fetchSource(key).then((text) => (s.source = text));
	});
</script>

<div class="page item node">
	{#if owner}
		<p class="muted"><code>{key}</code> has no page of its own. It is part of <a href={keyUrl(m, key)}>{m.nodes[owner].title ?? owner}</a>.</p>
	{:else if !node}
		<p class="muted">The manifest has no node <code>{key}</code>.</p>
	{:else if node.conflict?.length}
		<p class="conflicted" data-testid="conflicted">
			Defined in two files: {#each node.conflict as f, i (f)}{#if i}{' and '}{/if}<code>{f}</code>{/each}. It has no text until one definition moves or is forked — see <a href={route('/problems?code=duplicate-id')}>problems</a>.
		</p>
	{:else if held.verbatim && held.source}
		<pre class="verbatim" data-testid="verbatim" aria-label="the LaTeX behind this block">{held.source}</pre>
	{:else}
		<div class="gutters-host">
			<div class="gutters">
				<div class="column">
					<!-- `margins` so Show ids puts the id and state in the gutter, as in a document; a digest node's text is read, not written, so it is not authoring -->
					<FragmentNotes holder={held} fallback={key}>
						<Fragment path={node.fragment} macroSet={node.digest ?? ''} margins comments={slots} authoring={!node.external} annotations={held.notes} anchor={item.anchor ?? ''} jump={item.seq} />
					</FragmentNotes>
					{#if missingProof}<p class="muted absent" data-testid="missing-proof">No proof is attached.</p>{/if}
					{#if node.children.length}
						<ul class="plain children">
							{#each node.children as ck (ck)}
								<li><a href={nodeUrl(ck)}>{m.nodes[ck]?.taxon ?? ''} {m.nodes[ck]?.title ?? ck}</a></li>
							{/each}
						</ul>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	/* the pane's head is the top edge of the view, as a document's is: the gutter takes the left, the column the rest */
	.item.node {
		padding-left: 0;
		padding-right: 0;
	}
	.absent {
		margin: var(--gap) 0 0;
	}
	.children {
		margin-top: var(--gap-wide);
		font-family: var(--sans);
		font-size: 13px;
	}
	.conflicted {
		max-width: var(--measure);
		margin: 0 var(--gap-wide);
		font-size: 12px;
		line-height: 1.6;
		color: var(--ink-soft);
		padding: var(--gap-tight);
		border: 1px dashed var(--state-conflicted);
		border-radius: var(--rad-card);
		background: var(--state-conflicted-wash);
	}
	.verbatim {
		margin: 0 var(--gap-wide);
		white-space: pre-wrap;
		overflow-x: auto;
		font-size: 0.85em;
		line-height: 1.5;
		background: var(--leaf);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: var(--gap-tight) var(--gap);
	}
</style>
