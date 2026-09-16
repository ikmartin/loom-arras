<script lang="ts">
	// One component tree, three arrangements (book 15.8). The page renders no navigation and receives no shell props; a page that needs a right rail fills the `rail` snippet.
	import RailSections from './RailSections.svelte';
	import TopBarTabs from './TopBarTabs.svelte';
	import IconStrip from './IconStrip.svelte';
	import { prefs } from '$lib/prefs.svelte';
	import type { ShellProps } from './props';

	let props: Omit<ShellProps, 'children' | 'rail'> & { children: ShellProps['children']; rail?: ShellProps['rail'] } = $props();

	const Shell = $derived(prefs.shell === 'a' ? RailSections : prefs.shell === 'b' ? TopBarTabs : IconStrip);
</script>

<Shell {...props} />
