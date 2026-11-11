<script lang="ts">
	// What it did: a session's command log read as its record. **Recorded** groups the annotations it made or changed by the block they are on, each with its colour (the dot, which opens it), where it stands and its words on one line; **Ran** lists every other command once, with how many times and when last, and links what it names, a moved document under where it is now. **Every line, in order** keeps the log as it is, newest at the bottom, so nothing in it is hidden (V3). The dot is in the annotation's own colour and named by its type, a reply's a ring.
	import type { Annotation } from '$lib/manifest/types';
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import { didOf, type Named } from '$lib/sessions/did';
	import { when } from '$lib/sessions/when';
	import { keyName } from '$lib/workspace/names';
	import { lookVars, typeName } from '$lib/review/annotationTypes';
	import type { Item } from '../item';
	import { recordOf } from './session';

	let { item }: { item: Item } = $props();

	const m = $derived(store.manifest!);
	const log = $derived(recordOf(m, item.id).log ?? []);
	const did = $derived(didOf(m, log));

	/** What an annotation is on: a block by the name a reader uses, a note on a work's page by the work and the page. */
	function on(key: string, a?: Annotation): string {
		if (a?.target.page != null) {
			const work = Object.values(m.references).find((r) => r.work === key || r.works?.includes(key));
			return `${work?.citekey ?? key} p.${a.target.page}`;
		}
		return keyName(m, key);
	}
	const standing = (a: Annotation) => (a.discarded ? 'withdrawn' : a.status);
	const kindOf = (a: Annotation) => (a.in_reply_to ? `reply, ${typeName(m, a)}` : typeName(m, a));
	const named = (n: Named) => ('key' in n ? { href: `quilt:${n.key}`, text: keyName(m, n.key), title: n.key } : { href: `quilt:${n.path}`, text: n.path.split('/').pop() ?? n.path, title: n.path });

	function clock(stamp: string): string {
		const d = new Date(stamp);
		return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
	}
</script>

<div class="did" data-testid="session-did">
	{#if log.length}
		{#if did.recorded.length}
			<section data-testid="did-recorded">
				<h3>Recorded <span class="n">{did.recorded.reduce((n, r) => n + r.annotations.length, 0)}</span></h3>
				<ul class="groups">
					{#each did.recorded as r (r.key)}
						<li class="group" data-testid="did-group">
							<a class="on" href="quilt:{r.key}" title={r.key} data-testid="did-on">{on(r.key, r.annotations[0])}</a>
							<ul class="anns">
								{#each r.annotations as a (a.id)}
									<!-- the row a mark's link travels back to -->
									<li class="ann" id="ann-{a.id}">
										<a class="go" href="quilt:{a.id}" title="{kindOf(a)}: open it where it is" data-testid="did-annotation"><span class="ann-dot" class:reply={!!a.in_reply_to} style={lookVars(a.look)} role="img" aria-label={kindOf(a)} data-testid="did-kind"></span></a>
										<div class="first" data-testid="did-first"><Prose html={a.body_html} /></div>
										<span class="state state-{standing(a)}" data-testid="did-state">{standing(a)}</span>
									</li>
								{/each}
							</ul>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
		{#if did.ran.length}
			<section data-testid="did-ran">
				<h3>Ran <span class="n">{did.ran.length} {did.ran.length === 1 ? 'command' : 'commands'}</span></h3>
				<ul class="ran">
					{#each did.ran as r (r.command)}
						<li class="cmd" data-testid="did-command">
							<code class="command">{r.command}</code>
							<span class="times" data-testid="did-times">{r.count > 1 ? `×${r.count} · ` : ''}{when(r.last)} {clock(r.last)}</span>
							{#if r.names.length}
								<span class="names">{#each r.names as n, i (i)}{@const l = named(n)}<a href={l.href} title={l.title} data-testid="did-named">{l.text}</a>{/each}</span>
							{/if}
						</li>
					{/each}
				</ul>
			</section>
		{/if}
		<details class="every" data-testid="did-every">
			<summary>Every line, in order <span class="n">{log.length}</span></summary>
			<ol class="rows">
				{#each log as e, i (i)}
					<li class="row" data-testid="did-row">
						<span class="when" title={e.time}>{when(e.time)} {clock(e.time)}</span>
						<code class="command">{e.command}</code>
					</li>
				{/each}
			</ol>
		</details>
	{:else}
		<p class="empty muted">Nothing done through loom in this session yet.</p>
	{/if}
</div>

<style>
	.did {
		height: 100%;
		min-height: 0;
		overflow: auto;
		padding: var(--gap) var(--gap-wide);
		font-family: var(--sans);
		font-size: 12.5px;
	}
	h3 {
		font-size: 13px;
		font-weight: 500;
		margin: var(--gap) 0 6px;
	}
	.n,
	.times,
	.state {
		color: var(--ink-faint);
		font-size: 11.5px;
		font-weight: 400;
	}
	ul,
	ol {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.group {
		padding: 6px 0;
		border-bottom: 1px solid var(--rule);
	}
	.on {
		font-weight: 500;
	}
	.ann {
		display: flex;
		gap: 8px;
		align-items: baseline;
		padding: 2px 0 0 4px;
	}
	.go {
		flex: none;
		display: inline-flex;
		padding: 4px;
		margin: -4px 0;
	}
	/* its words typeset, on one line: the whole is a click away */
	.first {
		flex: 1;
		min-width: 0;
		max-height: 1.5em;
		overflow: hidden;
		color: var(--ink-soft);
	}
	.first :global(.body > *) {
		display: inline;
		margin: 0;
	}
	.first :global(.body) {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.state-open {
		color: var(--ink-soft);
	}
	.cmd {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 10px;
		align-items: baseline;
		padding: 4px 0;
		border-bottom: 1px solid var(--rule);
	}
	.command {
		background: none;
		padding: 0;
		font-family: var(--mono, ui-monospace, monospace);
		font-size: 11.5px;
		color: var(--ink-soft);
		overflow-wrap: anywhere;
	}
	.names {
		display: inline-flex;
		gap: 8px;
	}
	.every {
		margin-top: var(--gap);
	}
	.every summary {
		cursor: pointer;
		font-size: 13px;
	}
	.row {
		display: grid;
		grid-template-columns: 8.5rem minmax(0, 1fr);
		column-gap: var(--gap);
		padding: 3px 0;
		border-bottom: 1px solid var(--rule-faint, var(--rule));
	}
	.when {
		color: var(--ink-faint);
		font-size: 11px;
		padding-top: 1px;
	}
	.empty {
		margin: 0;
	}
</style>
