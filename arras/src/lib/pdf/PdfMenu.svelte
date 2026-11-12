<script lang="ts">
	// **PDF ▾**, the PDF's file acts on its toolbar: save a copy with what is annotated written into it, take in the annotations of another copy or of this one, edit its pages into a new file, and open it in its application. Where no publisher takes writes only saving a copy and editing pages remain, which need none.
	import ToolbarItem from '$lib/workspace/ToolbarItem.svelte';
	import ToolbarMenu from '$lib/workspace/ToolbarMenu.svelte';
	import type { MarkDesk } from './desk.svelte';

	let {
		desk,
		of,
		disabled = false,
		onoutside
	}: {
		desk: MarkDesk | null;
		/** What the menu acts on, for its accessible names. */
		of: string;
		disabled?: boolean;
		/** Open the file in its application; absent where it is not a project's file. */
		onoutside?: () => void;
	} = $props();

	let picker = $state<HTMLInputElement | null>(null);
	const off = $derived(disabled || !desk ? 'Open the PDF to act on it' : desk.busy ? 'Busy' : undefined);
</script>

<ToolbarMenu label="PDF" name="PDF menu for {of}" menuName="the PDF of {of}" testid="pdf-menu" menuTestid="pdf-menu-items" width={260} divided>
	<ToolbarItem label="Save a copy" name="save a copy of {of} with its annotations written in" {off} testid="mark-save-copy" onclick={() => void desk?.saveCopy()} />
	{#if desk?.writes}
		<ToolbarItem label="Take in from a PDF…" name="take in the annotations of another copy of {of}" {off} testid="mark-take-from" onclick={() => picker?.click()} />
		{#if desk.here}
			<ToolbarItem label="Take in {desk.here} from this PDF" name="take in the annotations {of} holds" {off} testid="mark-take-here" onclick={() => void desk?.takeHere()} />
		{/if}
	{/if}
	<ToolbarItem label="Edit pages…" name="turn, delete, reorder or insert pages of {of}, into a new file" {off} testid="mark-pages" onclick={() => desk && (desk.pages = true)} />
	{#if onoutside}
		<hr />
		<ToolbarItem label="Open in its application" name="open {of} in its application" testid="mark-outside" onclick={onoutside} />
	{/if}
</ToolbarMenu>
<input
	bind:this={picker}
	type="file"
	accept="application/pdf,.pdf"
	hidden
	aria-label="the PDF whose annotations to take in, for {of}"
	data-testid="mark-take-file"
	onchange={(e) => {
		const f = e.currentTarget.files?.[0];
		e.currentTarget.value = '';
		if (f) void desk?.takeFrom(f);
	}}
/>
