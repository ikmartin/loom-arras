<script lang="ts">
	// The navigation shell (book 15.8). A page renders no navigation of its own and receives no shell props; a page that needs a right rail fills the `rail` snippet.
	//
	// There was a second arrangement, shell A: a single rail with a View list at its head and no icon column. It is retired. Two arrangements meant every panel change had to be made twice, and the second one fell behind on the first change that was not — it kept a document dropdown, an Indexes section and no Library at all.
	import IconStrip from './IconStrip.svelte';
	import type { ShellProps } from './props';

	let props: Omit<ShellProps, 'children' | 'rail'> & { children: ShellProps['children']; rail?: ShellProps['rail'] } = $props();
</script>

<IconStrip {...props} />
