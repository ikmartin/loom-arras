<script lang="ts">
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import Fragment from '$lib/fragments/Fragment.svelte';
	import { masterStem } from '$lib/nav';

	const m = $derived(store.manifest!);
	const stem = $derived(decodeURIComponent(page.params.stem ?? ''));
	const master = $derived(m.masters.find((x) => masterStem(x.path) === stem));
	const sections = $derived(
		Object.values(m.nodes).filter((n) => n.kind === 'section' && master && n.reached_by.includes(master.path)).sort((a, b) => (a.numbers[master!.path]?.number ?? a.id).localeCompare(b.numbers[master!.path]?.number ?? b.id, undefined, { numeric: true }))
	);
</script>

<main class="page master">
	{#if !master}
		<h1>Unknown master</h1>
	{:else}
		<p class="muted">
			<code>{master.path}</code>{master.numbering_known ? '' : ' · not yet compiled: ids shown without numbers'}
			{#if master.pdf}· <a href={'/build/' + master.pdf}>PDF</a>{/if}
		</p>
		<div class="with-rail">
			<aside class="rail">
				<strong>Contents</strong>
				<ul>
					{#each sections as s (s.id)}
						<li style="margin-left: {(m.nodes[s.id]?.parent[master.path] ? 1 : 0) * 0.8}rem"><a href={'/node/' + s.id}>{s.numbers[master.path]?.number ?? ''} {s.title}</a></li>
					{/each}
				</ul>
			</aside>
			<div class="doc">
				<Fragment path={master.fragment} />
			</div>
		</div>
	{/if}
</main>

<style>
	.with-rail {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.5rem;
	}
	@media (min-width: 60rem) {
		main.master {
			max-width: 72rem;
		}
		.with-rail {
			grid-template-columns: 14rem minmax(0, 1fr);
		}
	}
	.rail {
		font-size: 0.85rem;
		position: sticky;
		top: 1rem;
		align-self: start;
	}
	.rail ul {
		list-style: none;
		padding: 0;
	}
	.rail li {
		margin: 0.2rem 0;
	}
</style>
