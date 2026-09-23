<script lang="ts">
	// The rail above every reading view: the annotation filter, then what the page says about itself, then the page's controls. One short strip in place of the bands that used to stand between the top of the window and the document's first line.
	//
	// The layout draws it once; a page fills it through `ReadingActs`, so no route builds a control row of its own. Its height is `--reading-rail`, which a page that sizes itself to the window subtracts.
	import SessionFilter from '$lib/sessions/SessionFilter.svelte';
	import { acts } from './acts.svelte';
</script>

<div class="reading-rail" data-testid="reading-rail">
	<div class="lead">
		<SessionFilter />
		{#if acts.lead}{@render acts.lead()}{/if}
	</div>
	<div class="acts">{#if acts.acts}{@render acts.acts()}{/if}</div>
</div>

<style>
	.reading-rail {
		display: flex;
		align-items: center;
		gap: var(--gap, 12px);
		height: var(--reading-rail);
		padding: 0 var(--gap, 12px);
		border-bottom: 1px solid var(--rule, #ddd9cf);
		font-size: 0.8rem;
	}
	.lead {
		display: flex;
		align-items: center;
		gap: var(--gap, 12px);
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
