<script lang="ts">
	// Asserted links between results (plan 0.12 §7), and the side-by-side that makes one judgeable.
	//
	// **Nobody checked these.** A relation between two statements has no page span to verify it against, so the surface says so rather than implying a machine agreed. What it does instead is make the judgement cheap: opening a link puts the two results' own page text side by side, which is how a person settles "these define the same notion" — by reading both. That is a human check, and this claims nothing more.
	import { store } from '$lib/manifest/client.svelte';
	import Tex from '$lib/math/Tex.svelte';
	import { keyUrl } from '$lib/nav';
	import type { AssertedLink } from '$lib/manifest/types';

	let {
		forKeys = null,
		heading = 'Links'
	}: {
		/** The results this list is about; `null` shows every link. A work passes all of its own, a result passes one. */
		forKeys?: string[] | null;
		heading?: string;
	} = $props();

	const m = $derived(store.manifest!);
	const want = $derived(forKeys ? new Set(forKeys) : null);
	const links = $derived((m.links ?? []).filter((l) => !want || want.has(l.from) || want.has(l.to)));
	let open = $state('');

	const READS: Record<string, string> = {
		'same-notion': 'defines the same notion as',
		generalises: 'generalises',
		specialises: 'is a special case of',
		'depends-on': 'depends on',
		contradicts: 'contradicts'
	};

	/** What a result reads as: its own page text where it has one, else the taxon and title the corpus knows. */
	function facts(id: string): { text: string; where: string } {
		for (const ref of Object.values(m.references)) {
			const r = ref.results?.[id];
			if (r) return { text: r.source_text ?? '', where: r.page ? `p.${r.page}` : ref.citekey };
		}
		const n = m.nodes[m.keys[id]?.node ?? id];
		return { text: '', where: n ? (n.taxon ?? '') : '' };
	}

	const other = (l: AssertedLink) => (want?.has(l.from) ? l.to : l.from);
</script>

{#if links.length}
	<section class="links" data-testid="links">
		<h2>{heading}</h2>
		<p class="muted asserted">
			Asserted, not checked — a relation has no page to verify it against. Open one to read both statements' own
			words side by side, which is how you settle it.
		</p>
		<ul class="plain">
			{#each links as l (l.id)}
				{@const a = facts(l.from)}
				{@const b = facts(l.to)}
				<li>
					<p class="claim">
						<a href={keyUrl(m, l.from)}>{l.from}</a>
						<em>{READS[l.kind] ?? l.kind}</em>
						<a href={keyUrl(m, l.to)}>{l.to}</a>
					</p>
					<p class="why"><Tex text={l.why} /> <span class="by">— {l.by || 'unattributed'}</span></p>
					{#if a.text || b.text}
						<button
							class="as-link"
							onclick={() => (open = open === l.id ? '' : l.id)}
							aria-expanded={open === l.id}
							data-testid="link-open-{l.id}">{open === l.id ? '▾' : '▸'} read both</button
						>
					{/if}
					{#if open === l.id}
						<div class="beside" data-testid="link-beside">
							<section>
								<h4>{l.from} <span class="where">{a.where}</span></h4>
								<p class="verbatim">{a.text || 'no page text recorded'}</p>
							</section>
							<section>
								<h4>{l.to} <span class="where">{b.where}</span></h4>
								<p class="verbatim">{b.text || 'no page text recorded'}</p>
							</section>
						</div>
					{/if}
					{#if want}<span class="sr">{other(l)}</span>{/if}
				</li>
			{/each}
		</ul>
	</section>
{/if}

<style>
	.links li {
		padding: var(--gap-tight) 0;
		border-top: 1px solid var(--rule);
	}
	.asserted {
		font-size: 0.9em;
	}
	.claim {
		margin: 0;
	}
	.claim em {
		font-style: italic;
		color: var(--ink-soft);
		margin: 0 0.35em;
	}
	.why {
		margin: 0.2em 0 0.3em;
		color: var(--ink-soft);
	}
	.by {
		color: var(--ink-faint);
		font-size: 0.9em;
	}
	.beside {
		display: grid;
		gap: var(--gap-tight);
		grid-template-columns: 1fr;
		margin-top: var(--gap-hair);
		padding: var(--gap-tight);
		background: var(--leaf);
		border-radius: var(--rad-control);
	}
	@media (min-width: 46rem) {
		.beside {
			grid-template-columns: 1fr 1fr;
		}
	}
	.beside h4 {
		margin: 0 0 0.25em;
		font-family: var(--sans);
		font-size: 0.72em;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--ink-faint);
		font-weight: 500;
	}
	.where {
		text-transform: none;
		letter-spacing: 0;
	}
	.verbatim {
		margin: 0;
		font-family: var(--mono);
		font-size: 0.82em;
		line-height: 1.5;
		white-space: pre-wrap;
	}
	.sr {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
	}
</style>
