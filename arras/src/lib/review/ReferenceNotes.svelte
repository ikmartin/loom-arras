<script lang="ts">
	// Works an agent proposed citing, and what became of the suggestion (plan 0.11 Part H).
	//
	// Two lists in one place, because they are two halves of one errand: the citation suggestions still open on this key, each linked to its annotation, whose box is where it is accepted or rejected (15.3.4a), and the works already accepted for it. An accepted note is a breadcrumb and never a second source of identity truth -- `verified` stays false until a person puts the identifier in the bibliography, and nothing here enters a closure.
	import { store } from '$lib/manifest/client.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { openOn } from '$lib/annotations';

	let { forKey }: { forKey: string } = $props();

	const m = $derived(store.manifest!);
	const notes = $derived((m.reference_notes ?? []).filter((n) => n.for?.includes(forKey)));
	const open = $derived(
		openOn(m, forKey).filter((a) => a.kind === 'citation' && a.status === 'open')
	);
</script>

{#if notes.length || open.length}
	<section class="refnotes" data-testid="reference-notes">
		{#if open.length}
			<p class="head">Suggested citations</p>
			<ul class="plain">
				{#each open as a (a.id)}
					<li>
						{#if a.payload}<span class="work"><TexProse text={a.payload} /></span>{/if}
						<Prose html={a.body_html} />
						<!-- the one rule for a link to an annotation (15.2.4): it opens what the annotation is on, with its box open -->
						<p class="actions"><a href="quilt:{a.id}" data-testid="refnote-open">open the suggestion</a></p>
					</li>
				{/each}
			</ul>
		{/if}
		{#if notes.length}
			<p class="head">Accepted, not yet in the bibliography</p>
			<ul class="plain">
				{#each notes as n, i (i)}
					<li>
						<span class="work">{n.work}</span>
						<span class="who">{n.accepted?.who ?? ''}</span>
						{#if !n.identifier?.verified}<span class="unverified">identifier unconfirmed</span>{/if}
					</li>
				{/each}
			</ul>
		{/if}
	</section>
{/if}

<style>
	.refnotes {
		font-size: 0.85em;
	}
	.head {
		font-family: var(--sans);
		font-size: 0.8em;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--ink-faint);
		margin: var(--gap) 0 var(--gap-tight);
	}
	li + li {
		margin-top: var(--gap-tight);
	}
	.actions {
		margin: 0.2em 0 0;
		font-family: var(--sans);
		font-size: 0.9em;
	}
	.who,
	.unverified {
		color: var(--ink-faint);
		font-size: 0.9em;
	}
	.unverified {
		color: var(--state-stale, var(--ink-faint));
	}
</style>
