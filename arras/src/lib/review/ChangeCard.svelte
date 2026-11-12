<script lang="ts">
	// One pending change as a card: what it is and who made it, its words out and in (struck and underlined in teal), what a suggestion's writer says of it and the annotation it answers, why it cannot be kept or discarded where it cannot, and Keep and Discard, which act as its popup's do (`history.svelte.ts`). In the list beside a text a click opens it at its words; in Review it names where it is and links there.
	import Icon from '$lib/components/Icon.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import type { PendingChange } from '$lib/manifest/types';
	import { placeUrl } from '$lib/nav';
	import { keyName, linkName } from '$lib/workspace/names';
	import { can } from '$lib/write';
	import { actSays, kindName, ready, refusal, whoMade } from './changes';
	import { discardChanges, keepChanges } from './history.svelte';
	import { say } from './toasts.svelte';

	let {
		c,
		on = false,
		onopen,
		place = false
	}: {
		c: PendingChange;
		/** Whether its popup is open. */
		on?: boolean;
		/** Open it at its words; absent where the card is not in the text's list. */
		onopen?: () => void;
		/** Say where it is, with a link there, as Review does. */
		place?: boolean;
	} = $props();

	const m = $derived(store.manifest);
	const says = $derived(actSays(c));
	const why = $derived(refusal(c));
	const answers = $derived(c.answers ? m?.annotations[c.answers] : undefined);
	const who = $derived(whoMade(m, c));

	let allowed = $state({ keep: false, discard: false });
	$effect(() => {
		void can('change-keep').then((ok) => (allowed.keep = ok));
		void can('change-discard').then((ok) => (allowed.discard = ok));
	});

	async function act(how: 'keep' | 'discard', e: Event): Promise<void> {
		e.stopPropagation();
		const res = how === 'keep' ? await keepChanges({ changes: [c.id] }) : await discardChanges({ changes: [c.id] });
		const refused = res.refused?.find((r) => r.id === c.id)?.why;
		if (!res.ok || refused) say({ title: how === 'keep' ? 'Not kept' : 'Not discarded', lines: [refused ?? res.error?.message ?? 'the publisher refused it'] });
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
	class="card ccard"
	class:on
	class:opens={!!onopen}
	role={onopen ? 'button' : undefined}
	tabindex={onopen ? 0 : undefined}
	data-testid="change-card"
	data-change={c.id}
	data-kind={c.kind}
	onclick={() => onopen?.()}
	onkeydown={(e) => e.key === 'Enter' && e.target === e.currentTarget && onopen?.()}
>
	<div class="ch">
		<span class="ck">{kindName(c)}</span>
		{#if who}<span class="who">{who}</span>{/if}
		<span>{c.kind === 'suggested' ? shortDate(c.created ?? '') : 'since your look'}</span>
	</div>
	{#if place && m}
		<div class="where" data-testid="change-where">
			{#if c.key}<a href={placeUrl(m, c.key)} onclick={(e) => e.stopPropagation()}>{keyName(m, c.key)}</a> · {/if}<code>{c.path}</code>
		</div>
	{/if}
	<div class="dx" data-testid="change-words">
		{#if c.old}<span class="del"><TexProse text={c.old} /></span>{/if}
		{#if c.old && c.new}{' '}{/if}
		{#if c.new}<span class="ins"><TexProse text={c.new} /></span>{/if}
	</div>
	{#if c.comment_html}<div class="ct"><Prose html={c.comment_html} /></div>{/if}
	{#if answers && m}<div class="ct none" data-testid="change-card-answers">It answers <a href={placeUrl(m, answers.target.key, answers.id, answers.in)} onclick={(e) => e.stopPropagation()}>{linkName(m, `quilt:${answers.id}`)}</a>.</div>{/if}
	{#if why}<div class="ct none" data-testid="change-card-why">{why}</div>{/if}
	<div class="acts">
		<button type="button" class="btn small primary" disabled={!ready(c) || !allowed.keep} title={says.keep} data-testid="card-keep" onclick={(e) => void act('keep', e)}><Icon name="check" size={12} />Keep</button>
		<button type="button" class="btn small" disabled={!ready(c) || !allowed.discard} title={says.discard} data-testid="card-discard" onclick={(e) => void act('discard', e)}><Icon name="close" size={12} />Discard</button>
	</div>
</div>

<style>
	.ccard {
		display: grid;
		gap: 6px;
		padding: 9px 10px;
		font-family: var(--sans);
		font-size: 12.5px;
		color: var(--ink);
		background: var(--sheet);
		border: 1px solid var(--rule);
		border-radius: 8px;
	}
	.ccard.opens {
		cursor: pointer;
	}
	.ccard.opens:hover {
		border-color: var(--rule-strong);
	}
	.ccard.on {
		border-color: var(--accent);
	}
	.ch {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
		font-size: 12px;
		color: var(--ink-faint);
	}
	.ck {
		flex: none;
		padding: 1px 7px;
		font-size: 11px;
		font-weight: 600;
		white-space: nowrap;
		color: var(--change);
		background: var(--change-wash);
		border-radius: 10px;
	}
	.who {
		color: var(--ink-soft);
		font-weight: 500;
	}
	.where {
		font-size: 12px;
		color: var(--ink-soft);
		overflow-wrap: anywhere;
	}
	.where code {
		font-family: var(--mono);
		font-size: 11.5px;
	}
	.dx {
		font-family: var(--body-face);
		font-size: 13.5px;
		line-height: 1.45;
		overflow-wrap: anywhere;
	}
	.del {
		color: color-mix(in srgb, var(--change) 70%, var(--sheet));
		text-decoration: line-through;
	}
	.ins {
		color: var(--change);
		text-decoration: underline;
		text-underline-offset: 3px;
	}
	.ct {
		line-height: 1.45;
	}
	.ct :global(p) {
		margin: 0.2em 0;
	}
	.ct.none {
		font-size: 12px;
		color: var(--ink-soft);
	}
	.acts {
		display: flex;
		gap: 6px;
	}
	.acts :global(.btn) {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
</style>
