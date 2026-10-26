<script lang="ts">
	// A session (plan 0.14, 0.20.1): two readings. What was said in it is its `Transcript`; read on its own it is being audited — `What it did`. Its views, leading the pane's tab strip, switch between them, as a work's do.
	import type { Item } from '../item';
	import ChatView from './ChatView.svelte';
	import SessionDid from './SessionDid.svelte';

	let { item }: { item: Item } = $props();
</script>

{#if item.view === 'did'}<SessionDid {item} />{:else}<ChatView {item} />{/if}
