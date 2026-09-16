<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/theme.css';
	import { store } from '$lib/manifest/client.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import Palette from '$lib/components/Palette.svelte';
	import { masterUrl } from '$lib/nav';

	let { children } = $props();

	onMount(() => store.start(1000));
	onDestroy(() => store.stop());

	const m = $derived(store.manifest);
	const errors = $derived(m ? m.diagnostics.filter((d) => d.severity === 'error').length : 0);
	const warnings = $derived(m ? m.diagnostics.filter((d) => d.severity === 'warning').length : 0);
	const defaultMaster = $derived(m?.masters.find((x) => x.default) ?? m?.masters[0]);
</script>

<svelte:head>
	<title>{m ? m.corpus.root_label : 'arras'}</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<header class="top">
	<a class="brand" href="/">{m ? m.corpus.root_label : 'arras'}</a>
	<nav>
		{#if defaultMaster}<a href={masterUrl(defaultMaster.path)}>paper</a>{/if}
		<a href="/review">review</a>
		<a href="/problems">problems</a>
		<a href="/blockers">blockers</a>
		<a href="/graph">graph</a>
		<a href="/tags">tags</a>
		<a href="/taxa">taxa</a>
		<a href="/references">references</a>
		<a href="/threads">threads</a>
		<a href="/loose">loose</a>
	</nav>
	{#if m}
		<span class="counts" data-testid="counts">{Object.keys(m.nodes).length} nodes · {errors} errors · {warnings} warnings</span>
	{/if}
</header>

{#if store.problem && !m}
	<main class="page">
		<h1>Problems</h1>
		<Diagnostics items={[store.problem]} />
	</main>
{:else if !m}
	<main class="page"><p class="muted">Loading manifest…</p></main>
{:else}
	{@render children()}
{/if}

<Palette />
