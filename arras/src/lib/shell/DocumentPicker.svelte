<script lang="ts">
	// The document picker: which document the read and graph views are about (book 15.2). Two groups, because a corpus has two kinds of document: the landmarks it has recorded and the drafts being worked on (book 17.1).
	import { goto } from '$app/navigation';
	import type { CanonDoc, Master } from '$lib/manifest/types';
	import { canonUrl, masterUrl } from '$lib/nav';

	let {
		masters,
		canon = [],
		current
	}: { masters: Master[]; canon?: CanonDoc[]; current: string } = $props();

	// newest landmark first: the one a reader is most likely to want
	const landmarks = $derived([...canon].reverse());

	function go(path: string) {
		const hit = canon.find((c) => c.path === path);
		void goto(hit ? canonUrl(hit.path) : masterUrl(path));
	}
</script>

<select aria-label="Document" value={current} onchange={(e) => go((e.currentTarget as HTMLSelectElement).value)}>
	{#if landmarks.length}
		<optgroup label="Canon">
			{#each landmarks as x (x.path)}
				<option value={x.path}>{x.title || x.stem}{x.step ? ' \u00b7 @' + Number(x.step) : ''}</option>
			{/each}
		</optgroup>
	{/if}
	{#if masters.length}
		<optgroup label="Working Drafts">
			{#each masters as x (x.path)}
				<option value={x.path}>{x.title || x.path}</option>
			{/each}
		</optgroup>
	{/if}
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
