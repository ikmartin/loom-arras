<script lang="ts">
	import { onDestroy, onMount, untrack } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import favicon from '$lib/assets/favicon.svg';
	import '$lib/theme.css';
	import { store } from '$lib/manifest/client.svelte';
	import Diagnostics from '$lib/components/Diagnostics.svelte';
	import Palette from '$lib/components/Palette.svelte';
	import LinkPreview from '$lib/components/LinkPreview.svelte';
	import PdfViewer from '$lib/components/PdfViewer.svelte';
	import NavShell from '$lib/shell/NavShell.svelte';
	import GlobalRail from '$lib/workspace/GlobalRail.svelte';
	import Workspace from '$lib/workspace/Workspace.svelte';
	import { workspace } from '$lib/workspace/store.svelte';
	import { interceptLinks } from '$lib/workspace/links';
	import { indexesOf, viewsOf, viewOf } from '$lib/shell/views';
	import { contentsOf } from '$lib/contents';
	import { reading } from '$lib/reading.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import { openPalette } from '$lib/palette';
	import { ensureMathJax } from '$lib/math/mathjax';
	import { masterStem } from '$lib/nav';
	import { rail } from '$lib/shell/rail.svelte';
	import { panel } from '$lib/shell/panel.svelte';
	import { sessionView } from '$lib/sessions/sessions.svelte';

	let { children } = $props();

	onMount(() => {
		prefs.load();
		sessionView.load();
		store.start(1000);
	});

	// A stored selection the corpus no longer lists is dropped once, on the first manifest; after that a session just made with `+ new` is briefly missing from the manifest and must survive it.
	let checked = false;
	$effect(() => {
		const mm = store.manifest;
		if (!mm || checked) return;
		checked = true;
		untrack(() => {
			const id = sessionView.selected;
			if (id && !(mm.sessions ?? []).some((s) => s.id === id) && !mm.threads[id]) sessionView.clear();
		});
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

	// Reading mode is the things a reader reads (plan 0.13.3): documents, works, nodes, a node's context and sessions, each an item in the workspace; `/thread/<id>` is a session's old address. The tables, the graph and home render full width outside it.
	const READING = new Set(['/master/[stem]', '/canon/[stem]', '/node/[...key]', '/library/[citekey]', '/context/[...key]', '/session/[id]', '/thread/[id]']);
	const inReading = $derived(READING.has(page.route.id ?? ''));
	$effect(() => {
		workspace.onScreen = inReading;
	});
	/** The current item, when it is a document: the panel's contents follow the focused pane (S3), and hang under nothing when it holds something else. */
	const currentItemDoc = $derived(inReading && workspace.current?.kind === 'document' ? workspace.current.id : '');
	const onDocument = $derived(!!currentItemDoc);

	// The document the shell is about: the current item in reading mode; elsewhere, what the URL names or the default.
	const currentDoc = $derived.by(() => {
		if (currentItemDoc) return currentItemDoc;
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
	// The panel's position bar follows the reader's scroll through the current document, which the document itself tracks (`followReading`, in its pane); the hash stands in only outside reading mode.
	const currentSection = $derived(reading.section || (!inReading && page.url.hash ? page.url.hash.slice(1) : ''));

	// **The URL is what is on screen** (plan 0.13.3): the left pane's item as the path, the right pane's as `?beside`. A URL the workspace did not write — a load, a link from outside reading mode, the palette — is taken in; every change the workspace makes is written back, replacing rather than pushing, since nothing in the workspace replaces anything a reader would go back to.
	let written = '';
	const here = () => page.url.pathname + page.url.search + page.url.hash;
	$effect(() => {
		const href = here();
		if (!m || !inReading || href === written) return;
		untrack(() => workspace.apply(m, href));
	});
	$effect(() => {
		if (!m || !inReading) return;
		const next = workspace.canonical(m);
		if (!next || next === untrack(here)) return;
		written = next;
		void goto(next, { replaceState: true, noScroll: true, keepFocus: true });
	});
	onMount(() =>
		interceptLinks(
			() => inReading,
			() => store.manifest
		)
	);
</script>

<svelte:head>
	<title>{m ? m.corpus.name : 'arras'}</title>
	<link rel="icon" href={favicon} />
</svelte:head>

<NavShell
	label={m ? m.corpus.name : 'arras'}
	views={viewsOf(m)}
	indexes={indexesOf(m)}
	currentView={viewOf(page.url.pathname)}
	masters={m?.masters ?? []}
	canon={m?.canon ?? []}
	{currentDoc}
	{contents}
	{currentSection}
	{onDocument}
	counts={{ errors, warnings }}
	search={openPalette}
	rail={rail.snippet && !inReading ? pageRail : undefined}
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
	{:else if inReading}
		<GlobalRail />
		<Workspace />
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
