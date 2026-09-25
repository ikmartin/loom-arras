<script lang="ts">
	// A session (plan 0.14): two errands, two readings. Talked to while working it is its `Chat`; read on its own it is being audited — `What it did`. The rail's cluster switches between them, as it does a work's views.
	import type { Item } from '../item';
	import ChatView from './ChatView.svelte';
	import SessionDid from './SessionDid.svelte';

	let { item }: { item: Item } = $props();
</script>

{#if item.view === 'did'}<SessionDid {item} />{:else}<ChatView {item} />{/if}
