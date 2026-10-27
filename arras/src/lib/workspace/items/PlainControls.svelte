<script lang="ts">
	// The toolbar of a kind with no controls of its own (a context, a session): its views where it has them, and *view*, which holds the pane's own line.
	import type { Item } from '../item';
	import ItemToolbar from '../ItemToolbar.svelte';

	let { name }: { item: Item; name: string } = $props();
</script>

<ItemToolbar {name} />
