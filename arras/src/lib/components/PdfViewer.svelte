<script lang="ts">
	// The PDF viewer (book 15.3.7): a link into a cited work, `cited:<scheme>:<value>#page=N`, opens the fetched paper at that page in the browser's own renderer. A link naming an artifact that is not on this machine says so and offers the identifier's own resolver instead, and a copy of a different version of the work is offered only with a warning, since that is where page numbers disagree.
	// It opens only where the copy on file is not the artifact a link names: a link to a filed copy opens that work as an item, and which pane it opens in is `workspace/links.ts`'s to decide.
	import { store } from '$lib/manifest/client.svelte';
	import { pdf } from '$lib/pdf.svelte';
	import { locate } from '$lib/worklink';
	import { bibText } from '$lib/works';
	import Popover from './Popover.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import Icon from './Icon.svelte';
	import PdfDoc from '$lib/pdf/PdfDoc.svelte';
	import PdfTools from '$lib/pdf/PdfTools.svelte';
	import { PdfView } from '$lib/pdf/view.svelte';

	const m = $derived(store.manifest);
	const link = $derived(pdf.link);
	const target = $derived(m && link ? locate(m, link) : null);
	let anyway = $state(false);
	/** The modal's view of the paper, which its own tools act on. */
	const paper = new PdfView();

	$effect(() => {
		void link;
		anyway = false;
	});

	const title = $derived(target?.ref ? bibText(target.ref.bib.title) || target.ref.citekey : link?.id ?? '');
	// The URL without the fragment: the renderer is told which page to open, rather than a browser plugin being asked.
	const shown = $derived(target?.local?.split('#')[0] ?? (anyway && target?.otherCopy ? target.otherCopy.url : ''));
	const opensAt = $derived(link?.page ?? 1);
</script>

{#if link && target}
	<Popover modal open label="the paper {title}" testid="pdf-viewer" onclose={() => pdf.close()}>
		<div class="viewer">
			<header>
				<div class="what">
					<span class="title"><Tex text={title} /></span>
					<span class="id">{link.id}{link.page ? ` · page ${link.page}` : ''}</span>
				</div>
				{#if shown}<PdfTools view={paper} />{/if}
				{#if shown}<a class="tab" href={shown} target="_blank" rel="noopener" data-testid="pdf-open-tab">open in a tab</a>{/if}
				<button class="close" onclick={() => pdf.close()} aria-label="Close the paper" title="close"><Icon name="close" size={14} /></button>
			</header>
			{#if link.quote}
				<p class="look" data-testid="pdf-quote">Look for “{link.quote}”.{link.page ? '' : ' The link names no page, so the paper opens at its start.'}</p>
			{/if}
			{#if shown}
				<div class="frame" data-testid="pdf-frame">
					<PdfDoc url={shown} page={opensAt} view={paper} />
				</div>
			{:else}
				<div class="absent" data-testid="pdf-absent">
					{#if target.otherCopy}
						<p><strong>The copy on this machine is a different version.</strong> This link names <code>{link.id}</code>; the copy here is <code>{target.otherCopy.id}</code>. A preprint and its published article are numbered and paginated differently, so {link.page ? `page ${link.page}` : 'the place this link means'} may not be the same place in it.</p>
						<p class="actions">
							<button class="as-link" onclick={() => (anyway = true)} data-testid="pdf-open-anyway">open the copy here anyway</button>
							{#if target.external}<a href={target.external} target="_blank" rel="noopener">open {link.id} at its source</a>{/if}
						</p>
					{:else}
						<p><strong>This paper has not been fetched on this machine.</strong> Fetched papers are kept out of version control, so a collaborator's copy of the corpus has the link without the paper.</p>
						{#if target.external}<p class="actions"><a href={target.external} target="_blank" rel="noopener" data-testid="pdf-external">open {link.id}{link.page && link.id.startsWith('arxiv:') ? ` at page ${link.page}` : ''} at its source</a></p>{/if}
						{#if !target.ref}<p class="faint">Nothing in this corpus cites a work with this identifier.</p>{/if}
					{/if}
				</div>
			{/if}
		</div>
	</Popover>
{/if}

<style>
	.viewer {
		width: min(90vw, 1000px);
		height: min(90vh, 1200px);
		display: flex;
		flex-direction: column;
	}
	header {
		display: flex;
		align-items: center;
		gap: var(--gap);
		padding: var(--gap-tight) var(--gap);
		border-bottom: 1px solid var(--rule);
		background: var(--leaf);
		font-family: var(--sans);
	}
	.what {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.title {
		font-family: var(--body-face);
		font-size: 14px;
		color: var(--ink);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.id {
		font-family: var(--mono);
		font-size: 10px;
		color: var(--ink-faint);
	}
	.tab {
		font-size: 11px;
		white-space: nowrap;
	}
	.close {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		color: var(--ink-soft);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-pill);
		cursor: pointer;
	}
	.look {
		margin: 0;
		padding: var(--gap-hair) var(--gap);
		font-family: var(--sans);
		font-size: 11px;
		color: var(--state-stale);
		background: var(--state-stale-wash);
	}
	.frame {
		flex: 1;
		width: 100%;
		min-height: 0;
		background: var(--leaf);
	}
	.absent {
		padding: var(--gap-wide);
		max-width: 38rem;
		font-family: var(--sans);
		font-size: 12px;
		line-height: 1.6;
		color: var(--ink-soft);
	}
	.absent strong {
		color: var(--ink);
		font-weight: 500;
	}
	.actions {
		display: flex;
		gap: var(--gap);
		flex-wrap: wrap;
	}
</style>
