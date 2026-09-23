<script lang="ts">
	// A node's context (plan 0.13.3 C1–C2, phase 4): what it is in, where its text came from, what it depends on and rests on, what uses it, which discussions touched it, the citations suggested for it, what was discarded on it, and the local graph, in one column opened beside the node by its `context` control. Everything about the node that is not the node: the node's own pane draws its statement and proofs alone.
	//
	// **Laid out as its design is** (phase 5): the lists first — where the node is, where it came from, what it depends on and what uses it — each result named as a reader names it (`Theorem 3.1`, a proof as the proof of its result), the key kept as each link's title; the local graph last and small, one expand away.
	//
	// **Absences are omitted, not reported.** A node no document reaches shows no `in` heading, and one nothing depends on shows no `depends on`: nobody asks whether a thing is in nothing, and a heading over "nothing" is the system answering a question the reader has not got.
	import { store } from '$lib/manifest/client.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import RailList from '$lib/components/RailList.svelte';
	import LocalGraphPanel from '$lib/graph/LocalGraphPanel.svelte';
	import { keyUrl, nodeUrl, readUrl, tagUrl, threadUrl, workUrl } from '$lib/nav';
	import { nodeName } from '../names';
	import { onAny, repliesTo } from '$lib/annotations';
	import AnnotationBox from '$lib/components/AnnotationBox.svelte';
	import Locator from '$lib/components/Locator.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import ClosurePanel from '$lib/review/ClosurePanel.svelte';
	import ReferenceNotes from '$lib/review/ReferenceNotes.svelte';
	import { versionLabel } from '$lib/badges';
	import type { Item } from '../item';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const key = $derived(item.id);
	const node = $derived(m.nodes[key]);
	const stmt = $derived(m.keys[key]);

	function chain(masterPath: string): string[] {
		const out: string[] = [];
		let cur = node?.parent[masterPath];
		let guard = 0;
		while (cur && guard++ < 20) {
			out.unshift(cur);
			cur = m.nodes[cur]?.parent[masterPath];
		}
		return out;
	}

	// One line per result, not one per edge or per key: a statement and its two proofs all using the same lemma is one dependency, and a use from a proof is a use by the result the proof belongs to, so listing each said nothing several times.
	function collapse(edges: { from: string; to: string; kind: string }[], side: 'to' | 'from') {
		const out = new Map<string, Set<string>>();
		for (const e of edges) {
			const at = e[side];
			// a use by an unlabelled proof is a use by its result; one *of* a proof names the proof, which is what it rests on
			const other = side === 'from' ? (m.keys[at]?.node ?? at) : at;
			if (other === key) continue;
			(out.get(other) ?? out.set(other, new Set()).get(other)!).add(e.kind);
		}
		return [...out.entries()].map(([k, kinds]) => ({ key: k, kinds: [...kinds].sort() }));
	}
	const deps = $derived(collapse(m.edges.filter((e) => e.from === key || node?.proofs.includes(e.from)), 'to'));
	const usedBy = $derived(collapse(m.edges.filter((e) => e.to === key || (node?.proofs ?? []).includes(e.to)), 'from'));
	// `unreachable` is "in no document" in the system's words: the problems page's business, and an absence here (C2)
	const diagnostics = $derived(m.diagnostics.filter((d) => d.keys.includes(key) && !/(^|:)unreachable$/.test(d.code)));
	const detached = $derived(onAny(m, [key, ...(node?.proofs ?? [])]).filter((a) => a.detached && !a.discarded));
	const threads = $derived(Object.values(m.threads).filter((t) => t.targets.includes(key) && !t.discarded));
	const closure = $derived(stmt?.closure.filter((k) => k !== key) ?? []);
	let restsOpen = $state(false);
	// Where the text came from: the landmark each of the node's keys was recorded at, said once per key that has one.
	const versions = $derived(
		[key, ...(node?.proofs ?? [])].map((k) => ({ key: k, label: versionLabel(m.keys[k]) })).filter((v) => v.label)
	);
	// Discarded annotations are nowhere else in reading mode; they are kept here, folded, only when there are any.
	const discarded = $derived(onAny(m, [key, ...(node?.proofs ?? [])]).filter((a) => a.discarded && a.in_reply_to === null));
	let showDiscarded = $state(false);
	// Both directions of every declared relation, grouped by kind; an unknown kind renders as a labelled link list like any other.
	const relations = $derived.by(() => {
		const out = new Map<string, string[]>();
		for (const r of m.relations ?? []) {
			const other = r.from === key ? r.to : r.to === key ? r.from : '';
			if (!other) continue;
			const list = out.get(r.kind) ?? [];
			if (!list.includes(other)) list.push(other);
			out.set(r.kind, list);
		}
		return [...out.entries()];
	});
	/** A result in a list, as a reader names it; a key that is no node's is named for the node that owns it. */
	const label = (k: string) => {
		if (m.nodes[k]) return nodeName(m, k);
		const owner = m.keys[k]?.node;
		return owner && m.nodes[owner] ? `proof of ${nodeName(m, owner)}` : k;
	};
	const file = (path: string) => path.split('/').pop() ?? path;
</script>

<div class="page item context" data-testid="context">
	{#if !node}
		<h1>Unknown key</h1>
		<p class="muted">The manifest has no node <code>{key}</code>.</p>
	{:else}
		{#if node.reached_by.length}
			<RailList label="in">
				{#each node.reached_by as mp (mp)}
					<p class="crumb">
						<a href={readUrl(mp, key)} title={mp}>{file(mp)}</a>
						{#each chain(mp) as ck (ck)}
							<span class="sep">›</span><a href={nodeUrl(ck)} title={ck}>{m.nodes[ck]?.title ?? ck}</a>
						{/each}
					</p>
				{/each}
			</RailList>
		{/if}

		{#if (node.external && node.digest) || versions.length || node.tags.length}
			<RailList label="from">
				{#if node.external && node.digest}
					<p class="line">
						<a href={workUrl(node.digest)}>{node.digest}</a>{#if node.locator}, <Locator ref={m.references[node.digest]} locator={node.locator} />{/if}
					</p>
				{/if}
				{#each versions as v (v.key)}<p class="line" data-testid="version"><code>{v.key}</code> {v.label}</p>{/each}
				{#if node.tags.length}<p class="line">{#each node.tags as t (t)}<a class="tag" href={tagUrl(t)}>#{t}</a> {/each}</p>{/if}
			</RailList>
		{/if}

		{#if deps.length}
			<RailList label="depends on">
				<ul class="plain">
					{#each deps as d (d.key)}
						<li><a href={keyUrl(m, d.key)} title={d.key}>{label(d.key)}</a> <span class="faint">{d.kinds.join(', ')}</span></li>
					{/each}
				</ul>
				{#if closure.length}<p class="faint">read first: {closure.length} more</p>{/if}
			</RailList>
			<!-- The graph answers "what would this disturb"; the stack answers "what does this rest on". Built only once opened: it renders other results in full. -->
			<details class="closure-open" data-testid="closure-open" bind:open={restsOpen}>
				<summary>what this rests on</summary>
				{#if restsOpen}<ClosurePanel center={key} />{/if}
			</details>
		{/if}

		{#if usedBy.length}
			<RailList label="used by">
				<ul class="plain">
					{#each usedBy as d (d.key)}
						<li><a href={keyUrl(m, d.key)} title={d.key}>{label(d.key)}</a> <span class="faint">{d.kinds.join(', ')}</span></li>
					{/each}
				</ul>
			</RailList>
		{/if}

		{#each relations as [kind, items] (kind)}
			<RailList label={kind === 'see' ? 'see also' : kind}>
				<ul class="plain" data-testid="relations-{kind}">
					{#each items as k (k)}
						<li>
							<a href={keyUrl(m, k)} title={k}>{label(k)}</a>
							<span class="faint">{m.nodes[k]?.reached_by?.length ? m.nodes[k].reached_by.join(', ') : m.publishes.documents ? 'no document' : ''}</span>
						</li>
					{/each}
				</ul>
			</RailList>
		{/each}

		{#if threads.length}
			<RailList label="discussions">
				<ul class="plain">
					{#each threads as t (t.id)}<li><a href={threadUrl(t.id)}>{t.title}</a></li>{/each}
				</ul>
			</RailList>
		{/if}

		{#if detached.length}
			<RailList label="detached comments">
				<ul class="plain">
					{#each detached as a (a.id)}<li><em><TexProse text={a.quote ?? ''} /></em></li>{/each}
				</ul>
			</RailList>
		{/if}

		<ReferenceNotes forKey={key} />

		{#if discarded.length}
			<p class="discarded">
				<button type="button" class="as-link" aria-pressed={showDiscarded} data-testid="show-discarded" onclick={() => (showDiscarded = !showDiscarded)}
					>{discarded.length} discarded — {showDiscarded ? 'hide' : 'show'}</button
				>
			</p>
			{#if showDiscarded}
				<div data-testid="discarded-list">
					{#each discarded as a (a.id)}<AnnotationBox annotation={a} replies={repliesTo(m, a.id)} />{/each}
				</div>
			{/if}
		{/if}

		{#if diagnostics.length}
			<RailList label="diagnostics">
				<Diagnostics items={diagnostics} />
			</RailList>
		{/if}

		<!-- Last and small: the lists answer the questions a reader brings, and the graph is the picture of them, one expand away from full size. Under its own title, which names it once; `hrefFor` makes it navigable (plan 0.11 Part D). -->
		<section class="graph"><LocalGraphPanel center={key} height={150} hrefFor={(id) => nodeUrl(id)} /></section>
	{/if}
</div>

<style>
	.item.context {
		max-width: 44rem;
		font-family: var(--sans);
		font-size: 12px;
	}
	.graph {
		margin-top: var(--gap-wide);
	}
	.crumb {
		font-size: 11px;
		margin: 0;
	}
	.line {
		margin: 0 0 2px;
	}
	.tag {
		margin-right: 4px;
	}
	.closure-open {
		margin: var(--gap-tight) 0 var(--gap);
	}
	.closure-open > summary {
		cursor: pointer;
		color: var(--ink-soft);
	}
	.discarded button {
		color: var(--ink-faint);
		font-size: 11px;
	}
	.crumb .sep {
		color: var(--ink-faint);
		margin: 0 3px;
	}
</style>
