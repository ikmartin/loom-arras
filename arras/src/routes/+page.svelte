<script lang="ts">
	import NoDrafts from '$lib/components/NoDrafts.svelte';
	// Home (book 15.3.4): four metric cards, then what needs attention, what is blocked, and where to go.
	import { store } from '$lib/manifest/client.svelte';
	import { canonUrl, keyUrl, masterUrl, nodeUrl } from '$lib/nav';
	import { route } from '$lib/paths';
	import { toneClass } from '$lib/state';

	const m = $derived(store.manifest!);
	const keys = $derived(Object.values(m.keys));
	const count = (state: string) => keys.filter((k) => k.state === state).length;
	const stale = $derived(keys.filter((k) => k.acceptance && k.acceptance.fresh === false));
	const incomplete = $derived(keys.filter((k) => k.state === 'incomplete'));
	const errors = $derived(m.diagnostics.filter((d) => d.severity === 'error'));
	const nodes = $derived(Object.values(m.nodes).filter((n) => n.kind !== 'section'));
	const loose = $derived(nodes.filter((n) => n.reached_by.length === 0));

	const cards = $derived([
		{ label: 'accepted', value: count('accepted'), tone: 'positive' },
		{ label: 'stale', value: stale.length, tone: 'warning' },
		{ label: 'incomplete', value: incomplete.length, tone: 'negative' },
		{ label: 'errors', value: errors.length, tone: errors.length ? 'negative' : 'neutral', href: '/problems?severity=error' }
	]);

	const title = (k: string) => {
		const n = m.nodes[m.keys[k]?.node ?? k] ?? m.nodes[k];
		return n ? `${n.taxon}${n.title ? ' · ' + n.title : ''}` : k;
	};
</script>

<main class="page">
	<h1>{m.corpus.root_label}</h1>
	<p class="muted">
		{m.publisher.name}
		{m.publisher.version} · interface {m.interface_version} · {nodes.length} nodes · {m.edges.length} edges
	</p>

	<div class="cards">
		{#each cards as c (c.label)}
			{#if c.href}
				<a class="card {toneClass(c.tone)}" href={c.href} data-testid="card-{c.label}">
					<span class="card-label">{c.label}</span>
					<span class="card-value">{c.value}</span>
				</a>
			{:else}
				<div class="card {toneClass(c.tone)}" data-testid="card-{c.label}">
					<span class="card-label">{c.label}</span>
					<span class="card-value">{c.value}</span>
				</div>
			{/if}
		{/each}
	</div>

	<h2>Documents</h2>
	{#if m.masters.length}
		<ul class="plain">
			{#each m.masters as master (master.path)}
				<li>
					<a href={masterUrl(master.path)}>{master.title || master.path}</a>
					<span class="faint">{master.path}{master.default ? ' · default' : ''}{master.numbering_known ? '' : ' · not yet numbered'}</span>
				</li>
			{/each}
		</ul>
	{:else}
		<NoDrafts what="documents to read" />
	{/if}

	{#if m.canon?.length}
		<h2>Canon</h2>
		<ul class="plain">
			{#each [...m.canon].reverse() as doc (doc.path)}
				<li>
					<a href={canonUrl(doc.path)}>{doc.title || doc.stem}</a>
					<span class="faint">{doc.step ? '@' + Number(doc.step) : doc.path}{doc.message ? ' · ' + doc.message : ''}</span>
				</li>
			{/each}
		</ul>
	{/if}

	<h2>Needs attention</h2>
	{#if stale.length || incomplete.length}
		<ul class="plain">
			{#each stale.slice(0, 8) as k (k.key)}
				<li><a href={keyUrl(m, k.key)}>{title(k.key)}</a> <span class="faint">stale since acceptance</span></li>
			{/each}
			{#each incomplete.slice(0, 8) as k (k.key)}
				<li><a href={keyUrl(m, k.key)}>{title(k.key)}</a> <span class="faint">incomplete</span></li>
			{/each}
		</ul>
		{#if stale.length > 8}<p class="faint">{stale.length} stale across drafting documents</p>{/if}
		{#if incomplete.length > 8}<p class="faint">{incomplete.length} incomplete across drafting documents</p>{/if}
	{:else}
		<p class="faint">nothing is stale and nothing is incomplete</p>
	{/if}

	<h2>Blocked</h2>
	{#if incomplete.length}
		<p>{incomplete.length} incomplete keys across drafting documents. <a href={route('/review')}>Review them by document</a>.</p>
	{:else}
		<p class="faint">nothing is blocked</p>
	{/if}

	{#if loose.length && m.publishes.documents}
		<h2>Not in any document</h2>
		<p><a href={route('/loose')}>{loose.length} nodes that no document includes</a></p>
	{/if}

	<h2>Recent</h2>
	<ul class="plain">
		{#each nodes.filter((n) => n.created).sort((a, b) => (b.created ?? '').localeCompare(a.created ?? '')).slice(0, 6) as n (n.id)}
			<li><a href={nodeUrl(n.id)}>{n.taxon}{n.title ? ' · ' + n.title : ''}</a> <span class="faint">{n.created}</span></li>
		{/each}
	</ul>
</main>

<style>
	.cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(118px, 1fr));
		gap: var(--gap-tight);
		max-width: 34rem;
		margin: var(--gap-wide) 0;
	}
	.card {
		height: 48px;
		background: var(--leaf);
		border-radius: var(--rad-control);
		padding: var(--gap-tight) var(--gap);
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 1px;
	}
	a.card:hover {
		text-decoration: none;
		background: var(--link-wash);
	}
	.card-label {
		font-family: var(--sans);
		font-size: 9px;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-faint);
	}
	.card-value {
		font-family: var(--sans);
		font-size: 18px;
		line-height: 1;
		color: var(--tone);
	}
</style>
