<script lang="ts">
	// Words drawn in a look, as a mark on the text draws them (theme.css `.ann-sample`): beside a type in a list, on the Annotate button, at the head of a popup.
	import type { Look } from '$lib/manifest/types';
	import { lookVars, styleOf } from './annotationTypes';

	let { look, text = 'Ab' }: { look: Partial<Look> | null | undefined; text?: string } = $props();
</script>

<span class="annotation ann-sample ann-{styleOf(look)}" style={lookVars(look)} data-testid="sample">{text}</span>
