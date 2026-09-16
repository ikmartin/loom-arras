<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { store } from '$lib/manifest/client.svelte';
	import { masterUrl, nodeUrl, threadUrl } from '$lib/nav';
	import { registerPalette } from '$lib/palette';

	let el: HTMLElement | undefined = $state();

	onMount(() => {
		void import('ninja-keys');
		registerPalette(() => (el as unknown as { open?: () => void } | undefined)?.open?.());
		return () => registerPalette(null);
	});

	type Item = { id: string; title: string; section: string; keywords?: string; handler: () => void };

	const data = $derived.by((): Item[] => {
		const m = store.manifest;
		if (!m) return [];
		return m.search.map((s) => {
			const url = s.kind === 'master' ? masterUrl(s.key) : s.kind === 'thread' ? threadUrl(s.key) : nodeUrl(s.key);
			return {
				id: s.key,
				title: `${s.key} ${s.title && s.title !== s.key ? '· ' + s.title : ''}`,
				section: s.taxon || s.kind || 'node',
				keywords: [...(s.aliases ?? []), ...(s.tags ?? []), s.excerpt ?? ''].join(' '),
				handler: () => void goto(url)
			};
		});
	});

	$effect(() => {
		if (el) (el as unknown as { data: Item[] }).data = data;
	});
</script>

<ninja-keys bind:this={el} placeholder="Search ids, titles, aliases, tags… (⌘K)"></ninja-keys>
