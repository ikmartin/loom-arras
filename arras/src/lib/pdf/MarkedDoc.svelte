<script lang="ts">
	// A PDF that can be marked (plan 0.28): the renderer with the markup bar above it, the card beside its marks and the pages editor over it. A word mark's tool turns a selection straight into a mark; with no tool up a selection goes to the caller, which offers what it offers.
	import { untrack, type ComponentProps } from 'svelte';
	import { store } from '$lib/manifest/client.svelte';
	import type { MarkDesk } from './desk.svelte';
	import MarkBar from './MarkBar.svelte';
	import MarkCard from './MarkCard.svelte';
	import { kindOf, ON_WORDS } from './marks';
	import PagesEditor from './PagesEditor.svelte';
	import PdfDoc from './PdfDoc.svelte';
	import type { PdfView } from './view.svelte';

	type DocProps = ComponentProps<typeof PdfDoc>;

	let {
		desk,
		view,
		url,
		name,
		dir = '',
		hidden = false,
		onoutside,
		page,
		share,
		seq,
		spans,
		focus = '',
		lands = true,
		onselect,
		onbox,
		onmark,
		onpage,
		onlink,
		onmoved
	}: {
		desk: MarkDesk;
		view: PdfView;
		url: string;
		/** The PDF's file name. */
		name: string;
		/** The project directory a page edit saves into by default. */
		dir?: string;
		/** The pane is hiding what is written on things, marks among them. */
		hidden?: boolean;
		/** Open the file in its application; absent where it is not a project's file. */
		onoutside?: () => void;
		page?: DocProps['page'];
		share?: DocProps['share'];
		seq?: DocProps['seq'];
		spans?: DocProps['spans'];
		focus?: string;
		lands?: DocProps['lands'];
		onselect?: DocProps['onselect'];
		onbox?: DocProps['onbox'];
		onmark?: DocProps['onmark'];
		onpage?: DocProps['onpage'];
		onlink?: DocProps['onlink'];
		onmoved?: DocProps['onmoved'];
	} = $props();

	let editing = $state(false);
	const wordTool = $derived(ON_WORDS.includes(view.tool) ? kindOf(view.tool) : null);

	// what the manifest now says lets go of what was on its way
	$effect(() => {
		void store.manifest;
		untrack(() => desk.settle());
	});

	// a link to a mark arrives looking at it
	let arrived = '';
	$effect(() => {
		const id = focus;
		if (!id || !lands || arrived === `${id}#${seq}` || !desk.marks.some((m) => m.id === id)) return;
		arrived = `${id}#${seq}`;
		untrack(() => desk.pick(id));
	});

	$effect(() => {
		const key = (e: KeyboardEvent) =>
			desk.key(e, () => {
				desk.flush();
				view.tool = 'select';
			});
		window.addEventListener('keydown', key);
		return () => window.removeEventListener('keydown', key);
	});

	// the tool is put down: the lines of ink drawn with it are one mark
	$effect(() => {
		if (view.tool !== 'ink') untrack(() => desk.flush());
	});
</script>

<div class="marked">
	{#if view.marking}
		<MarkBar {desk} {view} {onoutside} onpages={() => (editing = true)} />
	{/if}
	<div class="paper">
		<PdfDoc
			{url}
			{page}
			{share}
			{seq}
			{view}
			{spans}
			{focus}
			{lands}
			marks={hidden ? [] : desk.marks}
			selected={desk.selected}
			hide={desk.hides}
			onselect={(e) => {
				if (wordTool) {
					desk.markWords(wordTool, e);
					window.getSelection()?.removeAllRanges();
				} else onselect?.(e);
			}}
			onbox={(e) => {
				if (wordTool) desk.markRegion(wordTool, e);
				else onbox?.(e);
			}}
			{onmark}
			{onpage}
			{onlink}
			{onmoved}
			ondraw={(e) => desk.draw(e)}
			onpick={(e) => desk.pick(e.id)}
			onmove={(e) => desk.move(e)}
			onembedded={(e) => {
				desk.pick('');
				desk.reading = { subtype: e.subtype, body: e.body, by: e.by, at: e.client };
			}}
		/>
	</div>
	<MarkCard {desk} />
	{#if editing}
		<PagesEditor {desk} {url} {name} {dir} onclose={() => (editing = false)} />
	{/if}
</div>

<style>
	.marked {
		display: flex;
		flex-direction: column;
		flex: 1 1 auto;
		min-height: 0;
		height: 100%;
	}
	.paper {
		position: relative;
		flex: 1 1 auto;
		min-height: 0;
		display: flex;
	}
	.paper > :global(.doc) {
		flex: 1 1 auto;
		min-width: 0;
	}
</style>
