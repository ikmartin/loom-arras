<script lang="ts">
	// Where the list beside a text stands: against the pane's right edge, from under its toolbar to its foot, so it stays put while the text scrolls beside it. The text gives it room (`with-side` on the item).
	import { getPane } from '$lib/workspace/state.svelte';
	import SideList from './SideList.svelte';
	import type { Annotating } from './annotating.svelte';

	let { notes }: { notes: Annotating } = $props();

	const pane = getPane();

	function onPane(node: HTMLElement) {
		const frame = pane.frame() ?? node.parentElement;
		frame?.appendChild(node);
		const body = pane.scroller();
		const fit = () => (node.style.top = (body?.offsetTop ?? 0) + 'px');
		fit();
		const watch = new ResizeObserver(fit);
		if (frame) watch.observe(frame);
		return {
			destroy: () => {
				watch.disconnect();
				node.remove();
			}
		};
	}
</script>

{#if notes.side}
	<div class="side-host" use:onPane>
		<SideList {notes} />
	</div>
{/if}

<style>
	.side-host {
		position: absolute;
		right: 0;
		bottom: 0;
		z-index: 25;
		width: 310px;
		max-width: 100%;
	}
</style>
