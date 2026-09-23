<script lang="ts">
	// A session (plan 0.13.3 E1): two errands, two readings. Read while working it is a conversation beside its subject — `Discussion`; read on its own it is being audited — `What it did`. The rail's cluster switches between them, as it does a work's views.
	import type { Item } from '../item';
	import SessionDiscussion from './SessionDiscussion.svelte';
	import SessionDid from './SessionDid.svelte';

	let { item }: { item: Item } = $props();
</script>

{#if item.view === 'did'}<SessionDid {item} />{:else}<SessionDiscussion {item} />{/if}
