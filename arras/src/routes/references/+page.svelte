<script lang="ts">
	// The references index (book 10.2.9): every cited work, how to reach it outside the corpus, its digest, and what cites it.
	import { store } from '$lib/manifest/client.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import WorkLinks from '$lib/components/WorkLinks.svelte';
	import { digestUrl, keyUrl } from '$lib/nav';
	import { bibText } from '$lib/works';

	const m = $derived(store.manifest!);
	const refs = $derived(Object.values(m.references).sort((a, b) => a.citekey.localeCompare(b.citekey)));
	// A digest's own results cite the paper they come from, which says nothing about who uses it, so only the corpus's citations count here.
	const citers = (r: (typeof refs)[number]) => r.cited_by.filter((k) => m.nodes[m.keys[k]?.node ?? k]?.digest !== r.citekey);
	const SHOWN = 6;
	let expanded = $state(new Set<string>());
	const toggle = (ck: string) => {
		const next = new Set(expanded);
		if (next.has(ck)) next.delete(ck);
		else next.add(ck);
		expanded = next;
	};
</script>

<main class="page">
	<h1>References</h1>
	<table class="list">
		<thead><tr><th>work</th><th>links</th><th>digest</th><th>cited by</th></tr></thead>
		<tbody>
			{#each refs as r (r.citekey)}
				<tr>
					<td class="work">
						<a href={digestUrl(r.citekey)} class="title"><Tex text={bibText(r.bib.title) || r.citekey} /></a>
						<span class="byline">{bibText(r.bib.author)}{r.bib.year ? ` · ${r.bib.year}` : ''} · <code>{r.citekey}</code></span>
					</td>
					<td><WorkLinks ref={r} /></td>
					<td>{#if r.digest}<a href={digestUrl(r.citekey)}>{r.digest.nodes.length} results</a> <span class="faint">({r.digest.method})</span>{#if r.version_mismatch} <span class="problem">version mismatch</span>{/if}{:else}<span class="faint">none</span>{/if}</td>
					<td class="cited">
						{#each citers(r) as c, i (c)}{#if i < SHOWN || expanded.has(r.citekey)}{#if i}, {/if}<a href={keyUrl(m, c)}>{c}</a>{/if}{:else}<span class="faint">not cited</span>{/each}
						{#if citers(r).length > SHOWN}<button class="as-link more" onclick={() => toggle(r.citekey)}>{expanded.has(r.citekey) ? 'fewer' : `and ${citers(r).length - SHOWN} more`}</button>{/if}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</main>

<style>
	.work {
		max-width: 26rem;
	}
	.title {
		display: block;
		font-family: var(--body-face);
		font-size: 13px;
		line-height: 1.4;
	}
	.byline {
		display: block;
		font-family: var(--sans);
		font-size: 10px;
		color: var(--ink-faint);
		line-height: 1.5;
	}
	.byline code {
		font-size: 9px;
		background: none;
		padding: 0;
	}
	.cited {
		font-size: 11px;
		overflow-wrap: anywhere;
	}
	.more {
		margin-left: var(--gap-hair);
		font-size: 10px;
	}
</style>
