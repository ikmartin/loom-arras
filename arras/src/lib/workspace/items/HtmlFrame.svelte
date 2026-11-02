<script lang="ts">
	// An HTML file of the project in a frame of its own origin (plan 0.22.7): the publisher's frames origin, never the viewer's, so its scripts and embedded players run and it can never reach the write token. The frame keeps that origin and gets no top navigation; the bridge the publisher adds to the page asks this frame's owner to follow a link and says what is selected, and a message from anywhere but that frame is dropped.
	// Where the publisher runs no frames origin (a static host, a read-only server) the page is drawn from the viewer's origin with no script at all.
	import { onMount, untrack } from 'svelte';
	import { here } from '$lib/here.svelte';
	import { store } from '$lib/manifest/client.svelte';
	import { filesUrl } from '$lib/paths';
	import { capabilities } from '$lib/write';
	import { followFromFrame, paneOfElement } from '../links';
	import { workspace } from '../store.svelte';

	let { path, anchor = '', seq = 0, key }: { path: string; anchor?: string; seq?: number; key: string } = $props();

	let frame: HTMLIFrameElement | undefined = $state();
	/** The frames origin; `undefined` until the publisher has answered, `null` where it runs none. */
	let frames = $state<string | null | undefined>(undefined);
	/** The place the frame was sent to, set when a link is followed rather than each time the page reports a move. */
	let target = $state('');

	onMount(() => {
		void capabilities().then((c) => (frames = c?.frames ?? null));
	});
	$effect(() => {
		void seq;
		target = untrack(() => anchor);
	});

	const encoded = $derived(path.split('/').map(encodeURIComponent).join('/'));
	const hash = $derived(target ? '#' + encodeURIComponent(target) : '');
	const src = $derived(frames ? `${frames}/${encoded}?loom-viewer=${encodeURIComponent(location.origin)}${hash}` : filesUrl(path) + hash);

	$effect(() => {
		const origin = frames;
		if (!origin) return;
		const heard = (e: MessageEvent) => {
			if (e.origin !== origin || !frame || e.source !== frame.contentWindow) return;
			const said = e.data as { loom?: unknown; href?: unknown; text?: unknown; hash?: unknown } | null;
			const m = store.manifest;
			if (said?.loom === 'open' && typeof said.href === 'string' && m) followFromFrame(m, said.href, paneOfElement(frame));
			else if (said?.loom === 'selection' && typeof said.text === 'string') {
				if (said.text) here.selection = { item: key, file: path, text: said.text.slice(0, 4000) };
				else if (here.selection?.item === key) here.selection = null;
			} else if (said?.loom === 'place' && typeof said.hash === 'string') workspace.update(key, { anchor: said.hash || undefined });
		};
		window.addEventListener('message', heard);
		return () => window.removeEventListener('message', heard);
	});
</script>

<div class="html-file" data-testid="file-item" data-kind="html">
	{#if frames !== undefined}
		{#if frames}
			<iframe
				bind:this={frame}
				title={path}
				{src}
				sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-forms allow-presentation"
				allow="fullscreen; autoplay; encrypted-media; picture-in-picture"
				data-testid="html-frame"
			></iframe>
		{:else}
			<iframe bind:this={frame} title={path} {src} sandbox="" data-testid="html-frame" data-scriptless></iframe>
		{/if}
	{/if}
</div>

<style>
	.html-file {
		height: 100%;
		min-height: 0;
		display: flex;
	}
	iframe {
		flex: 1;
		width: 100%;
		border: 0;
		background: var(--paper, #fff);
	}
</style>
