<script lang="ts">
	// The document picker: which master the read and graph views are about (book 15.2).
	import { goto } from '$app/navigation';
	import type { Master } from '$lib/manifest/types';
	import { masterUrl } from '$lib/nav';

	let { masters, current }: { masters: Master[]; current: string } = $props();
</script>

<select
	aria-label="Document"
	value={current}
	onchange={(e) => goto(masterUrl((e.currentTarget as HTMLSelectElement).value))}
>
	{#each masters as x (x.path)}
		<option value={x.path}>{x.title || x.path}</option>
	{/each}
</select>

<style>
	select {
		width: 100%;
		font-family: var(--sans);
		font-size: 11px;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: var(--rad-control);
		padding: 3px 6px;
	}
</style>
