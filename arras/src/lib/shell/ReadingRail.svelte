<script lang="ts">
	// The document view's top rail. One short strip in place of the four bands that used to stand between the top of the
	// window and the document's own title: an "About this document" block, a Comment button, the source path, and a row
	// of annotation controls beside a count of them.
	//
	// What the reader came for is the document, so what the application has to say about the document is a control at the
	// edge rather than a paragraph in the way. `lead` is empty on a master today and is where the document tabs go when
	// several documents can be open at once -- which is why the rail spans the content area and not the measured column.
	import type { Snippet } from 'svelte';

	let { lead, acts }: { lead?: Snippet; acts?: Snippet } = $props();
</script>

<div class="reading-rail" data-testid="reading-rail">
	<div class="lead">{#if lead}{@render lead()}{/if}</div>
	<div class="acts">{#if acts}{@render acts()}{/if}</div>
</div>

<style>
	.reading-rail {
		display: flex;
		align-items: center;
		gap: var(--gap, 12px);
		height: 36px;
		padding: 0 var(--gap, 12px);
		border-bottom: 1px solid var(--rule, #ddd9cf);
		font-size: 0.8rem;
	}
	.lead {
		display: flex;
		align-items: center;
		gap: var(--gap-tight, 6px);
		flex: 1 1 auto;
		min-width: 0;
		color: var(--ink-soft, #5f5e5a);
	}
	.acts {
		display: flex;
		align-items: center;
		gap: var(--gap, 12px);
		flex: 0 0 auto;
	}
</style>
