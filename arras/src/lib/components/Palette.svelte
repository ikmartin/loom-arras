<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { canonUrl, masterUrl, nodeUrl, threadUrl, workUrl } from '$lib/nav';
	import { bibText } from '$lib/works';

	let el: HTMLElement | undefined = $state();

	// ⌘K is ninja-keys' own hotkey, and the one way in: search is not offered as a control until it does more than find by id and title
	onMount(() => {
		void import('ninja-keys');
	});

	type Item = { id: string; title: string; section: string; keywords?: string; handler: () => void };

	const data = $derived.by((): Item[] => {
		const m = store.manifest;
		if (!m) return [];
		// the cited works too, by key and title, each opening its paper: the palette is the one search, and a work is a thing a reader opens
		const works = Object.values(m.references ?? {}).map((r) => ({
			id: `work:${r.citekey}`,
			title: `${r.citekey} · ${bibText(r.bib.title) || r.citekey}`,
			section: 'work',
			keywords: bibText(r.bib.author ?? ''),
			handler: () => void goto(workUrl(r.citekey))
		}));
		const found = m.search.map((s) => {
			const url =
				s.kind === 'master'
					? masterUrl(s.key)
					: s.kind === 'canon'
						? canonUrl(s.key)
						: s.kind === 'thread'
							? threadUrl(s.key)
							: nodeUrl(s.key);
			return {
				id: s.key,
				title: `${s.key} ${s.title && s.title !== s.key ? '· ' + s.title : ''}`,
				section: s.taxon || s.kind || 'node',
				keywords: [...(s.aliases ?? []), ...(s.tags ?? []), s.excerpt ?? ''].join(' '),
				handler: () => void goto(url)
			};
		});
		return [...found, ...works];
	});

	$effect(() => {
		if (el) (el as unknown as { data: Item[] }).data = data;
	});
</script>

<ninja-keys bind:this={el} placeholder="Search ids, titles, aliases, tags… (⌘K)"></ninja-keys>
