<script lang="ts">
	// A pending change's popup, opened at its words, or at the element it is marked on where it is not merged into the text (`apart`): what it is (an edit in the file, or a suggestion, with who wrote it and when), its words out and in and its patch where the text does not show them, the annotations on its words, each of which opens its own popup, what a suggestion's writer says of it, a box that writes an annotation on its words, and Keep and Discard. Both take effect on screen at once (`history.svelte.ts`); a change that is not ready says why and offers neither.
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import DiffView from '$lib/components/DiffView.svelte';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import { placeUrl } from '$lib/nav';
	import { linkName } from '$lib/workspace/names';
	import { can } from '$lib/write';
	import { typeOf } from './annotationTypes';
	import { actSays, changeById, kindName, ready, refusal, whoMade } from './changes';
	import { annotate, discardChanges, keepChanges } from './history.svelte';
	import { say } from './toasts.svelte';

	let {
		id,
		here = [],
		apart = false,
		onclose,
		onannotation
	}: {
		id: string;
		/** The annotations whose marks stand on its words, by id. */
		here?: string[];
		/** Marked beside its words rather than drawn in them, so the popup shows them. */
		apart?: boolean;
		onclose: () => void;
		/** Open annotation `id`'s popup at its mark, in place of this one. */
		onannotation?: (id: string) => void;
	} = $props();

	const m = $derived(store.manifest);
	const c = $derived(changeById(m, id));
	const says = $derived(c ? actSays(c) : null);
	const why = $derived(c ? refusal(c) : '');
	const on = $derived(here.map((x) => m?.annotations[x]).filter((a) => !!a && !a.in_reply_to));
	const answers = $derived(c?.answers ? m?.annotations[c.answers] : undefined);

	// kept or discarded, here or elsewhere, it takes its popup with it
	$effect(() => {
		if (m && !c) onclose();
	});

	let allowed = $state({ keep: false, discard: false, annotate: false });
	onMount(() => {
		void can('change-keep').then((ok) => (allowed.keep = ok));
		void can('change-discard').then((ok) => (allowed.discard = ok));
		void can('annotate').then((ok) => (allowed.annotate = ok));
	});

	let text = $state('');
	let busy = $state(false);
	let said = $state('');

	/** Keep or discard it: the popup closes at once, the text shows the change done, and a refusal is said. */
	async function act(how: 'keep' | 'discard'): Promise<void> {
		onclose();
		const res = how === 'keep' ? await keepChanges({ changes: [id] }) : await discardChanges({ changes: [id] });
		const refused = res.refused?.find((r) => r.id === id)?.why;
		if (!res.ok || refused) say({ title: how === 'keep' ? 'Not kept' : 'Not discarded', lines: [refused ?? res.error?.message ?? 'the publisher refused it'] });
	}

	/** Write an annotation on its words, as they stand in what the person has kept: the words it takes out, or its block where it only adds. */
	async function comment(): Promise<void> {
		if (!c || !text.trim()) return;
		busy = true;
		said = '';
		const target = c.key ?? c.documents[0] ?? c.path;
		const res = await annotate({ target, ...(c.old.trim() ? { quote: c.old } : {}), message: text.trim() });
		busy = false;
		if (!res.ok) said = res.error?.message ?? 'The publisher refused it.';
		else {
			text = '';
			said = c.old.trim() ? 'Written as an annotation on these words.' : 'Written as an annotation on its block.';
		}
	}
</script>

{#if c && says}
	<div class="ann-popup change-popup" data-testid="change-popup" data-change-id={c.id} role="dialog" aria-label="{kindName(c)}{whoMade(m, c) ? ` by ${whoMade(m, c)}` : ''}">
		<div class="phead">
			<span class="ck" data-testid="change-kind">{kindName(c)}</span>
			<span class="meta">{c.kind === 'suggested' ? [whoMade(m, c), shortDate(c.created ?? '')].filter(Boolean).join(' · ') : 'made since your look'}</span>
			<button type="button" class="x" aria-label="Close" title="Close" data-testid="popup-close" onclick={onclose}><Icon name="close" size={14} /></button>
		</div>
		{#if apart}
			<div class="dx" data-testid="change-words">
				{#if c.old}<span class="del"><TexProse text={c.old} /></span>{/if}
				{#if c.old && c.new}{' '}{/if}
				{#if c.new}<span class="ins"><TexProse text={c.new} /></span>{/if}
			</div>
			{#if c.diff}<DiffView path={c.diff} />{/if}
		{/if}
		{#if on.length}
			<div class="here" data-testid="change-here">
				{on.length === 1 ? '1 annotation here: ' : `${on.length} annotations here: `}
				{#each on as a, i (a!.id)}{i ? ', ' : ''}<button type="button" class="lnk" data-testid="change-here-open" data-annotation={a!.id} onclick={() => onannotation?.(a!.id)}>{typeOf(m, a!)?.name ?? 'Annotation'} · {a!.author.label ?? a!.author.id}</button>{/each}
			</div>
		{/if}
		{#if answers && m}<div class="here" data-testid="change-answers">It answers <a href={placeUrl(m, answers.target.key, answers.id, answers.in)}>{linkName(m, `quilt:${answers.id}`)}</a>; Keep resolves it.</div>{/if}
		{#if c.comment_html}<div class="cmt shown" data-testid="change-comment"><Prose html={c.comment_html} /></div>{/if}
		{#if allowed.annotate}
			<textarea class="cmt" rows="2" placeholder="Add a comment" aria-label="Comment on these words" data-testid="change-comment-field" bind:value={text} disabled={busy}></textarea>
			{#if text.trim()}<div class="pact"><button type="button" class="btn small primary" disabled={busy} data-testid="change-comment-save" onclick={() => void comment()}>Comment</button></div>{/if}
		{/if}
		{#if said}<p class="said" role="status" data-testid="change-said">{said}</p>{/if}
		<div class="cfoot">
			<button type="button" class="btn small primary" disabled={!ready(c) || !allowed.keep} title={says.keep} data-testid="change-keep" onclick={() => void act('keep')}><Icon name="check" size={13} />Keep</button>
			<button type="button" class="btn small" disabled={!ready(c) || !allowed.discard} title={says.discard} data-testid="change-discard" onclick={() => void act('discard')}><Icon name="close" size={13} />Discard</button>
			<span class="cwhy" data-testid="change-why">{why || says.line}</span>
		</div>
	</div>
{/if}

<style>
	.ann-popup {
		display: flex;
		flex-direction: column;
		gap: 8px;
		box-sizing: border-box;
		width: 350px;
		max-width: 100%;
		padding: 10px 11px;
		font-family: var(--sans);
		font-size: 13px;
		color: var(--ink);
	}
	.phead {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.ck {
		flex: none;
		padding: 2px 8px;
		font-size: 11.5px;
		font-weight: 600;
		white-space: nowrap;
		color: var(--change);
		background: var(--change-wash);
		border-radius: 10px;
	}
	.meta {
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 12px;
		color: var(--ink-faint);
	}
	.x {
		display: grid;
		place-items: center;
		flex: none;
		width: 22px;
		height: 22px;
		margin-left: auto;
		padding: 0;
		color: var(--ink-faint);
		background: none;
		border: 0;
		border-radius: 4px;
		cursor: pointer;
	}
	.x:hover {
		background: var(--leaf);
		color: var(--ink);
	}
	.dx {
		max-height: 9em;
		overflow: auto;
		font-family: var(--body-face);
		font-size: 13.5px;
		line-height: 1.45;
		overflow-wrap: anywhere;
	}
	.del {
		color: var(--change);
		text-decoration: line-through;
	}
	.ins {
		color: var(--change);
		text-decoration: underline;
		text-underline-offset: 3px;
	}
	.here {
		font-size: 12px;
		line-height: 1.45;
		color: var(--ink-soft);
	}
	.lnk {
		padding: 0;
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.lnk:hover {
		text-decoration: underline;
	}
	.cmt {
		display: block;
		width: 100%;
		box-sizing: border-box;
		min-height: 52px;
		padding: 7px 8px;
		font-family: var(--body-face);
		font-size: 13.5px;
		line-height: 1.45;
		color: var(--ink);
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 6px;
		resize: none;
	}
	.cmt.shown {
		min-height: 0;
		padding: 2px 1px;
		background: transparent;
		border-color: transparent;
	}
	.cmt.shown :global(p) {
		margin: 0.2em 0;
	}
	.pact {
		display: flex;
		justify-content: flex-end;
	}
	.said {
		margin: 0;
		font-size: 12px;
		color: var(--ink-soft);
	}
	.cfoot {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.cfoot :global(.btn) {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
	.cwhy {
		margin-left: 4px;
		font-size: 11.5px;
		line-height: 1.3;
		color: var(--ink-faint);
	}
</style>
