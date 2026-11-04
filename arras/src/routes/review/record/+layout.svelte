<script lang="ts">
	// Review › Record: what has been done, under one heading, as tabs: each document's versions, the sessions, and every act the history recorded. Nothing here waits on the person but a version no document leads to.
	import '$lib/review/review.css';
	import type { Snippet } from 'svelte';
	import { page } from '$app/state';
	import { store } from '$lib/manifest/client.svelte';
	import { route } from '$lib/paths';
	import ReviewHeading from '$lib/review/ReviewHeading.svelte';

	let { children }: { children: Snippet } = $props();

	const tabs = $derived(
		[
			{ id: 'versions', label: 'Versions', href: route('/review/record'), route: '/review/record', when: true },
			{ id: 'sessions', label: 'Sessions', href: route('/review/record/sessions'), route: '/review/record/sessions', when: store.manifest?.publishes?.discussions !== false },
			{ id: 'acts', label: 'Everything recorded', href: route('/review/record/acts'), route: '/review/record/acts', when: true }
		].filter((t) => t.when)
	);
</script>

<main class="page review-page scrollbar-shown" data-testid="record">
	<ReviewHeading title="Record" />
	<nav class="tabs" aria-label="The record" data-testid="record-tabs">
		{#each tabs as t (t.id)}
			<a href={t.href} aria-current={page.route.id === t.route ? 'page' : undefined} data-testid="record-tab-{t.id}">{t.label}</a>
		{/each}
	</nav>
	{@render children()}
</main>

<style>
	.tabs {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin: -6px 0 var(--gap);
		border-bottom: 1px solid var(--rule);
	}
	.tabs a {
		padding: 7px 14px;
		margin-bottom: -1px;
		font-size: 13.5px;
		color: var(--ink-soft);
		text-decoration: none;
		border-bottom: 2px solid transparent;
	}
	.tabs a:hover {
		color: var(--ink);
	}
	.tabs a[aria-current='page'] {
		color: var(--ink);
		border-bottom-color: var(--review-accent);
	}
</style>
