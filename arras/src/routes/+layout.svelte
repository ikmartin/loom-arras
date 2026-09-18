<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/state';
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/theme.css';
	import { store } from '$lib/manifest/client.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import Palette from '$lib/components/Palette.svelte';
	import LinkPreview from '$lib/components/LinkPreview.svelte';
	import PdfViewer from '$lib/components/PdfViewer.svelte';
	import NavShell from '$lib/shell/NavShell.svelte';
	import { viewsOf, viewOf } from '$lib/shell/views';
	import { contentsOf } from '$lib/contents';
	import { followReading, reading, sectionIds } from '$lib/reading.svelte';
	import { prefs, type Shell } from '$lib/prefs.svelte';
	import { openPalette } from '$lib/palette';
	import { ensureMathJax } from '$lib/math/mathjax';
	import { masterStem } from '$lib/nav';
	import { rail } from '$lib/shell/rail.svelte';
	import { panel } from '$lib/shell/panel.svelte';

	let { children } = $props();

	onMount(() => {
		// `?shell=` beats the stored choice, so two shells can be compared by sending a link (book 15.2)
		const q = page.url.searchParams.get('shell');
		prefs.load(q === 'a' || q === 'c' ? { shell: q as Shell } : undefined);
		store.start(1000);
	});
	onDestroy(() => store.stop());

	// One effect owns the <html> attributes and the stored copy; app.html has already applied them once, before the first paint.
	$effect(() => prefs.apply());

	const m = $derived(store.manifest);

	// MathJax is two megabytes of script. Loading it while the browser is idle, once the corpus's macros are known, means the first page with mathematics does not wait for it.
	let warmed = false;
	$effect(() => {
		const mm = m;
		if (!mm || warmed) return;
		warmed = true;
		const warm = () => void ensureMathJax(mm.macros.default ?? []);
		if ('requestIdleCallback' in window) requestIdleCallback(warm, { timeout: 2000 });
		else setTimeout(warm, 200);
	});
	const errors = $derived(m ? m.diagnostics.filter((d) => d.severity === 'error').length : 0);
	const warnings = $derived(m ? m.diagnostics.filter((d) => d.severity === 'warning').length : 0);
	const defaultMaster = $derived(m?.masters.find((x) => x.default) ?? m?.masters[0]);

	// The document the shell is about: the one on screen in the read and graph views, the default elsewhere.
	// The route decides which kind, never the stem: a landmark and a draft may share one.
	const currentDoc = $derived.by(() => {
		const stem = page.params.stem;
		if (stem && m) {
			if (page.route.id?.startsWith('/canon')) {
				const c = m.canon?.find((x) => x.stem === stem);
				if (c) return c.path;
			} else {
				const hit = m.masters.find((x) => masterStem(x.path) === stem);
				if (hit) return hit.path;
			}
		}
		const g = page.url.searchParams.get('master');
		if (g && m?.masters.some((x) => x.path === g)) return g;
		return defaultMaster?.path ?? m?.canon?.[m.canon.length - 1]?.path ?? '';
	});

	// a landmark has no nodes, so it has no contents list of its own
	const isCanon = $derived(!!m?.canon?.some((c) => c.path === currentDoc));
	const contents = $derived(m && currentDoc && !isCanon ? contentsOf(m, currentDoc) : []);
	// The rail's position bar follows the scroll while a document is being read, and falls back to the hash
	// elsewhere. Reading the fragments' own element ids means it also lights for a section with no allocated id,
	// whose key is not slug-shaped and so never matched a hash.
	const reads = $derived(page.url.pathname.startsWith('/master'));
	$effect(() => {
		if (!reads) return;
		return followReading(sectionIds(contents));
	});
	const currentSection = $derived(reading.section || (page.url.hash ? page.url.hash.slice(1) : ''));
</script>

<svelte:head>
	<title>{m ? m.corpus.name : 'arras'}</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<NavShell
	label={m ? m.corpus.name : 'arras'}
	views={viewsOf(m)}
	currentView={viewOf(page.url.pathname)}
	masters={m?.masters ?? []}
	canon={m?.canon ?? []}
	{currentDoc}
	{contents}
	{currentSection}
	counts={{ nodes: m ? Object.keys(m.nodes).length : 0, errors, warnings }}
	search={openPalette}
	rail={rail.snippet ? pageRail : undefined}
	panel={panel.snippet ? pagePanel : undefined}
	panelLabel={panel.label}
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

{#snippet pageRail()}
	{#if rail.snippet}{@render rail.snippet()}{/if}
{/snippet}

{#snippet pagePanel()}
	{#if panel.snippet}{@render panel.snippet()}{/if}
{/snippet}

<Palette />
<LinkPreview />
<PdfViewer />
