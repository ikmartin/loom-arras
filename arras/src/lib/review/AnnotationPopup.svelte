<script lang="ts">
	// The one popup, for every annotation wherever it is drawn: its type and look (changeable from the head, with "Changed from" its type when the look differs from the type's), when the words it was written on are gone the words as they were and the version that holds them, its comment (edited in place), the replies and a reply, then Resolve where its type stays open and Delete. Given a `draft` instead of an id, it writes a new one: a comment at a place, or words marked with a type that asks something, which loom takes only with words.
	//
	// It reads the annotation from the manifest by id, so a write that comes back on the next poll is shown without the popup being made again, and an annotation deleted elsewhere closes it. Every write goes through the history (`history.svelte.ts`), so the toolbar's Undo takes it back. Each verb is offered only where the publisher serves its endpoint.
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Prose from '$lib/math/Prose.svelte';
	import TexProse from '$lib/math/TexProse.svelte';
	import { shortDate } from '$lib/badges';
	import { store } from '$lib/manifest/client.svelte';
	import type { Look } from '$lib/manifest/types';
	import { repliesTo } from '$lib/annotations';
	import { can, known, write, type WriteResult } from '$lib/write';
	import { linkName } from '$lib/workspace/names';
	import { staysOpen, typeOf } from './annotationTypes';
	import { changedFrom, earlier, hand, handPayload, lookOf, retype, typeById, typesPayload, withLook, withType, type Draft } from './annotating.svelte';
	import { annotate, edit, remove as removeAnnotation, reply as replyTo, resolve } from './history.svelte';
	import Changed from './Changed.svelte';
	import LookControls from './LookControls.svelte';
	import Sample from './Sample.svelte';
	import TypeList from './TypeList.svelte';
	import VersionView from './VersionView.svelte';
	import { openSettings } from '$lib/shell/settings/opener.svelte';

	let {
		id = '',
		draft,
		onclose,
		onwritten,
		onmark
	}: {
		id?: string;
		draft?: Draft;
		onclose: () => void;
		/** A draft was written, as the annotation `id` loom gave it. */
		onwritten?: (id: string) => void;
		/** A mark in the version this popup opened was clicked: open that annotation's popup. */
		onmark?: (trigger: HTMLElement, ids: string[]) => void;
	} = $props();

	const m = $derived(store.manifest);
	const a = $derived(id ? m?.annotations[id] : undefined);
	const types = $derived(m?.annotation_types ?? []);

	// an annotation deleted, here or elsewhere, takes its popup with it
	$effect(() => {
		if (id && m && !a) onclose();
	});

	const ENDPOINTS = ['annotate', 'edit', 'reply', 'resolve', 'delete', 'types-save'];
	let allowed = $state<Record<string, boolean>>(Object.fromEntries(ENDPOINTS.map((v) => [v, known(v) ?? false])));
	onMount(() => {
		for (const v of ENDPOINTS) void can(v).then((ok) => (allowed[v] = ok));
	});

	/** The look shown and the type chosen: the annotation's own, or, for a draft, what is in hand. */
	const look = $derived<Look>(a ? a.look : lookOf(m, hand.value));
	const current = $derived<string | null>(a ? (typeOf(m, a) ? a.type : null) : hand.type && types.some((t) => t.id === hand.type) ? hand.type : null);
	const typeName = $derived(current ? (types.find((t) => t.id === current)?.name ?? '') : 'No type');
	const changeable = $derived(draft ? true : allowed.edit);
	/** The type the look differs from, for the "Changed from" line. */
	const from = $derived(a ? changedFrom(m, a) : hand.type && Object.keys(hand.over).length ? (typeById(m, hand.type) ?? null) : null);

	let formatting = $state(false);
	let busy = $state(false);
	let said = $state('');

	/** The comment as words to edit: the published rendering with its markup taken out. */
	function words(html: string): string {
		const el = document.createElement('div');
		el.innerHTML = html;
		return (el.textContent ?? '').trim();
	}
	// the comment as written, so editing it keeps its Markdown and math; the rendered words only from a publisher that does not say
	const comment = $derived(a ? (a.body ?? words(a.body_html)) : '');
	/** Being edited: the text in the field, or null while the comment is shown. A draft, or an annotation with nothing said, starts in the field. */
	let text = $state<string | null>(null);
	const editing = $derived(text !== null || !!draft || (!!a && !comment && allowed.edit));
	const value = $derived(text ?? (draft ? '' : comment));
	const dirty = $derived(draft ? value.trim() !== '' : value.trim() !== comment);

	let reply = $state('');
	let showVersion = $state(false);

	/** Do one write, one at a time, and say loom's refusal where there is one; the result, or null when refused. */
	async function send(act: () => Promise<WriteResult>): Promise<string | null> {
		if (busy) return null;
		busy = true;
		said = '';
		const res = await act();
		busy = false;
		if (!res.ok) {
			said = res.error?.message ?? 'the publisher refused it';
			return null;
		}
		return res.result ?? '';
	}

	async function save(): Promise<void> {
		if (draft) {
			if (!value.trim()) return;
			const body = { target: draft.target, ...(draft.quote ? { quote: draft.quote } : {}), ...(draft.in ? { in: draft.in } : {}), ...(draft.extra ?? {}), ...handPayload(m, hand.value), message: value.trim() };
			const result = await send(() => annotate(body));
			if (result !== null) onwritten?.(result.split(/\s+/)[0] ?? '');
			return;
		}
		if (!a || !dirty) return;
		const at = a;
		if ((await send(() => edit(at, { message: value.trim() }))) !== null) text = null;
	}

	async function pickType(next: string | null): Promise<void> {
		if (draft) return hand.set(withType(m, hand.value, next));
		if (!a || next === current) return;
		const at = a;
		await send(() => edit(at, retype(m, at, next)));
	}

	async function pickLook(change: Partial<Look>, done: boolean): Promise<void> {
		if (draft) return hand.set(withLook(m, hand.value, change));
		if (!a || !done) return;
		const at = a;
		await send(() => edit(at, { look: change }));
	}

	/** Reset: the look the type gives, dropping what is set over it. */
	async function reset(): Promise<void> {
		if (!a) return hand.set({ type: hand.type, over: {} });
		const at = a;
		await send(() => edit(at, { look: null }));
	}

	/** Update the type: its look becomes this one's, written into the quilt's types, and this one follows it again. */
	async function update(): Promise<void> {
		const t = from;
		if (!t) return;
		const saved = await send(() => write('types-save', { types: typesPayload(m, t.id, look) }));
		if (saved === null) return;
		void store.refresh();
		if (!a) return hand.set({ type: t.id, over: {} });
		const at = a;
		await send(() => edit(at, { look: null }));
	}

	async function answer(): Promise<void> {
		if (!a || !reply.trim()) return;
		const at = a;
		const message = reply.trim();
		if ((await send(() => replyTo(at.id, message))) !== null) reply = '';
	}

	async function remove(target: string): Promise<void> {
		if (busy) return;
		busy = true;
		said = await removeAnnotation(target, m ? linkName(m, `quilt:${target}`) : 'an annotation');
		busy = false;
	}

	function keys(e: KeyboardEvent): void {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
			e.preventDefault();
			void save();
		}
	}

	function grow(el: HTMLTextAreaElement): void {
		el.style.height = 'auto';
		el.style.height = el.scrollHeight + 2 + 'px';
	}
	function field(el: HTMLTextAreaElement): void {
		grow(el);
		if (draft || text !== null) el.focus();
	}

	const replies = $derived(a && m ? repliesTo(m, a.id) : []);
	const asks = $derived(!!a && staysOpen(m, a));
	const version = $derived(a ? earlier(a) : null);
</script>

{#if a || draft}
	<div class="ann-popup" data-testid="ann-popup" data-annotation-id={a?.id ?? ''} role="dialog" aria-label={a ? `${typeName === 'No type' ? 'annotation' : typeName} by ${a.author.label ?? a.author.id}` : 'new annotation'}>
		<div class="phead">
			<button type="button" class="ptype" aria-expanded={formatting} disabled={!changeable} title={changeable ? 'Type and look' : undefined} data-testid="popup-type" onclick={() => (formatting = !formatting)}><Sample {look} text={typeName} />{#if changeable}<Icon name="caret" size={12} />{/if}</button>
			<span class="meta">{#if a}<span title={a.author.id}>{a.author.label ?? a.author.id}</span> · {shortDate(a.created)}{:else}{draft?.name}{/if}</span>
			<button type="button" class="x" aria-label="Close" title="Close" data-testid="popup-close" onclick={onclose}><Icon name="close" size={14} /></button>
		</div>
		{#if formatting && changeable}
			<div class="pformat" data-testid="popup-format">
				<TypeList {types} {current} {look} disabled={busy} onpick={(t) => void pickType(t)} onadd={allowed['types-save'] ? () => openSettings('annotations', { take: a ? { kind: 'annotation', id: a.id } : { kind: 'hand' } }) : undefined} />
				<LookControls {look} disabled={busy} onpick={(c, done) => void pickLook(c, done)} />
				{#if from}<Changed name={from.name} disabled={busy} onreset={() => void reset()} onupdate={allowed['types-save'] ? () => void update() : undefined} />{/if}
			</div>
		{/if}
		{#if a?.refound && a.target.page}
			<!-- a changed PDF keeps no version, so there is nothing to open: where the mark was found again is all there is to say -->
			<div class="earlier" data-testid="popup-refound">Found again on page {a.target.page} of the changed PDF.</div>
		{/if}
		{#if version}
			<div class="earlier" data-testid="popup-earlier">
				Written on earlier words: <span class="ow">“<TexProse text={version.words} />”</span>
				{#if version.fragment}<button type="button" class="lnk" data-testid="earlier-open" aria-expanded={showVersion} onclick={() => (showVersion = !showVersion)}>{showVersion ? 'Close that version' : 'Open that version'}</button>{/if}
			</div>
			{#if showVersion && a && version.fragment}<VersionView path={version.fragment} focus={a.id} {onmark} />{/if}
		{/if}
		{#if editing && (draft || allowed.edit)}
			<textarea class="cmt" rows="2" placeholder={draft?.quote === undefined && draft ? 'Write the comment' : 'Add a comment'} aria-label="Comment" data-testid="popup-comment-field" value={value} use:field oninput={(e) => { text = e.currentTarget.value; grow(e.currentTarget); }} onkeydown={keys}></textarea>
			{#if dirty || draft}
				<div class="pact">
					{#if text !== null && !draft}<button type="button" class="lnk" onclick={() => (text = null)}>Discard</button>{/if}
					<button type="button" class="btn small primary" disabled={busy || !dirty} data-testid="popup-save" onclick={() => void save()}>{draft ? (draft.quote ? 'Annotate' : 'Comment') : 'Save'}</button>
				</div>
			{/if}
		{:else if comment}
			<!-- svelte-ignore a11y_no_static_element_interactions, a11y_no_noninteractive_tabindex -->
			<div class="cmt shown" class:editable={allowed.edit} role={allowed.edit ? 'button' : undefined} tabindex={allowed.edit ? 0 : undefined} title={allowed.edit ? 'Click to edit' : undefined} data-testid="popup-comment" onclick={(e) => allowed.edit && !(e.target as Element).closest('a') && (text = comment)} onkeydown={(e) => allowed.edit && e.key === 'Enter' && (text = comment)}><Prose html={a?.body_html ?? ''} /></div>
		{/if}
		{#if a && (comment || replies.length)}
			<div class="thread" data-testid="popup-thread">
				{#each replies as r (r.id)}
					<div class="rep" data-testid="popup-reply-row" data-annotation-id={r.id}>
						<b title={r.author.id}>{r.author.label ?? r.author.id}</b>
						<Prose html={r.body_html} />
						{#if allowed.delete}<button type="button" class="lnk del" data-testid="reply-delete" disabled={busy} onclick={() => void remove(r.id)}>Delete</button>{/if}
					</div>
				{/each}
				{#if allowed.reply}<input class="reply" placeholder="Reply" aria-label="Reply" data-testid="popup-reply" disabled={busy} bind:value={reply} onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void answer(); } }} />{/if}
			</div>
		{/if}
		{#if a}
			<div class="pfoot">
				{#if asks}<span class="stat" class:done={a.status !== 'open'} title={a.status === 'open' ? 'Open: in To do for everyone but its writer, until someone resolves it' : 'Resolved: in nobody’s To do'} data-testid="popup-status">{a.status === 'open' ? 'Open' : 'Resolved'}</span>{/if}
				{#if allowed.resolve && a.status === 'open' && asks}<button type="button" class="lnk" disabled={busy} data-testid="popup-resolve" onclick={() => void send(() => resolve(a.id))}>Resolve</button>{/if}
				{#if allowed.resolve && a.status !== 'open'}<button type="button" class="lnk" disabled={busy} data-testid="popup-reopen" onclick={() => void send(() => resolve(a.id, true))}>Reopen</button>{/if}
				{#if allowed.delete}<button type="button" class="lnk del" disabled={busy} data-testid="popup-delete" onclick={() => void remove(a.id)}>Delete</button>{/if}
			</div>
		{/if}
		{#if said}<p class="said" role="alert" data-testid="popup-said">{said}</p>{/if}
	</div>
{/if}

<style>
	.ann-popup {
		display: flex;
		flex-direction: column;
		gap: 8px;
		box-sizing: border-box;
		width: 340px;
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
	.ptype {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		flex: none;
		max-width: 55%;
		padding: 1px 4px;
		font: inherit;
		font-size: 12.5px;
		font-weight: 600;
		color: var(--ink);
		background: none;
		border: 1px solid transparent;
		border-radius: 5px;
		cursor: pointer;
	}
	.ptype:hover:not(:disabled),
	.ptype[aria-expanded='true'] {
		border-color: var(--rule);
	}
	.ptype:disabled {
		cursor: default;
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
	.pformat {
		display: grid;
		gap: 10px;
		padding: 8px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: 6px;
	}
	.earlier {
		font-size: 12px;
		line-height: 1.45;
		color: var(--ink-soft);
	}
	.ow {
		font-family: var(--body-face);
		font-size: 13.5px;
		color: var(--ink);
	}
	.cmt {
		display: block;
		width: 100%;
		box-sizing: border-box;
		min-height: 58px;
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
	.cmt.shown.editable {
		cursor: text;
	}
	.cmt.shown.editable:hover {
		background: var(--leaf);
	}
	.cmt.shown :global(p) {
		margin: 0.2em 0;
	}
	.pact {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 12px;
		font-size: 12px;
	}
	.thread {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}
	.rep {
		padding-left: 9px;
		line-height: 1.4;
		border-left: 2px solid var(--rule);
	}
	.rep :global(p) {
		display: inline;
		margin: 0;
	}
	.rep .del {
		margin-left: 6px;
		font-size: 11.5px;
	}
	.reply {
		width: 100%;
		box-sizing: border-box;
		padding: 4px 7px;
		font: inherit;
		color: var(--ink);
		background: transparent;
		border: 1px solid var(--rule);
		border-radius: 6px;
	}
	.pfoot {
		display: flex;
		align-items: center;
		gap: 12px;
		font-size: 12px;
	}
	.pfoot .del {
		margin-left: auto;
		color: var(--ink-faint);
	}
	.stat {
		flex: none;
		padding: 1px 7px;
		font-size: 11px;
		font-weight: 600;
		white-space: nowrap;
		color: var(--accent);
		border: 1px solid var(--accent);
		border-radius: 9px;
	}
	.stat.done {
		color: var(--ink-faint);
		border-color: var(--rule-strong);
	}
	.lnk {
		padding: 0;
		font: inherit;
		color: var(--link);
		background: none;
		border: 0;
		cursor: pointer;
	}
	.lnk:hover:not(:disabled) {
		text-decoration: underline;
	}
	.lnk:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.said {
		margin: 0;
		font-size: 12px;
		color: var(--state-stale);
	}
</style>
