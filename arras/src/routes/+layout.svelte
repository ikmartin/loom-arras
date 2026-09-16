<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/state';
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/theme.css';
	import { store } from '$lib/manifest/client.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import Palette from '$lib/components/Palette.svelte';
	import NavShell from '$lib/shell/NavShell.svelte';
	import { viewsOf, viewOf } from '$lib/shell/views';
	import { contentsOf } from '$lib/contents';
	import { prefs, type Shell } from '$lib/prefs.svelte';
	import { openPalette } from '$lib/palette';
	import { masterStem } from '$lib/nav';

	let { children } = $props();

	onMount(() => {
		// `?shell=` beats the stored choice, so two shells can be compared by sending a link (book 15.2)
		const q = page.url.searchParams.get('shell');
		prefs.load(q === 'a' || q === 'b' || q === 'c' ? { shell: q as Shell } : undefined);
		store.start(1000);
	});
	onDestroy(() => store.stop());

	// One effect owns the <html> attributes and the stored copy; app.html has already applied them once, before the first paint.
	$effect(() => prefs.apply());

	const m = $derived(store.manifest);
	const errors = $derived(m ? m.diagnostics.filter((d) => d.severity === 'error').length : 0);
	const warnings = $derived(m ? m.diagnostics.filter((d) => d.severity === 'warning').length : 0);
	const defaultMaster = $derived(m?.masters.find((x) => x.default) ?? m?.masters[0]);

	// The document the shell is about: the one on screen in the read and graph views, the default elsewhere.
	const currentMaster = $derived.by(() => {
		const stem = page.params.stem;
		if (stem && m) {
			const hit = m.masters.find((x) => masterStem(x.path) === stem);
			if (hit) return hit.path;
		}
		const g = page.url.searchParams.get('master');
		if (g && m?.masters.some((x) => x.path === g)) return g;
		return defaultMaster?.path ?? '';
	});

	const contents = $derived(m && currentMaster ? contentsOf(m, currentMaster) : []);
	const currentSection = $derived(page.url.hash ? page.url.hash.slice(1) : '');
</script>

<svelte:head>
	<title>{m ? m.corpus.root_label : 'arras'}</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<NavShell
	label={m ? m.corpus.root_label : 'arras'}
	views={viewsOf(m)}
	currentView={viewOf(page.url.pathname)}
	masters={m?.masters ?? []}
	{currentMaster}
	{contents}
	{currentSection}
	counts={{ nodes: m ? Object.keys(m.nodes).length : 0, errors, warnings }}
	search={openPalette}
>
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
</NavShell>

<Palette />
