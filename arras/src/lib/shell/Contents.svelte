<script lang="ts">
	// The contents tree of the current document (book 15.2, 15.4). Identical in all three shells.
	import type { ContentsEntry } from '$lib/contents';
	import { readUrl } from '$lib/nav';
	import Tex from '$lib/math/Tex.svelte';

	let { entries, masterPath, current = '' }: { entries: ContentsEntry[]; masterPath: string; current?: string } = $props();
</script>

<nav class="contents rail-scroll" aria-label="Contents">
	<ul>
		{#each entries as e (e.key)}
			<li style="padding-left: {e.depth * 10}px">
				<a
					href={readUrl(masterPath, e.key)}
					aria-current={current === e.key ? 'true' : undefined}
					class:current={current === e.key}
				>
					{#if e.number}<span class="num">{e.number}</span>{/if}<Tex text={e.title} />
				</a>
			</li>
		{:else}
			<li class="faint">no sections</li>
		{/each}
	</ul>
</nav>

<style>
	.contents ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.contents li {
		margin: 1px 0;
	}
	.contents a {
		display: block;
		color: var(--ink-soft);
		font-size: 11px;
		line-height: 1.35;
		padding: 2px 4px 2px 6px;
		border-left: 2px solid transparent;
	}
	.contents a:hover {
		color: var(--ink);
		text-decoration: none;
	}
	.contents a.current {
		color: var(--ink);
		border-left-color: var(--link);
	}
	.num {
		color: var(--ink-faint);
		margin-right: 4px;
	}
</style>
